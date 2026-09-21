"""SMTP digest with TLS, durable cooldowns and a dry-run path."""
import argparse
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr, formatdate, make_msgid
import hashlib
import json
import os
from pathlib import Path
import smtplib
import ssl
from .store import atomic_json


def timestamp(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None:raise ValueError('Timezone required')
    return dt.timestamp()


def key(signal):
    return hashlib.sha256('|'.join(str(signal[k]) for k in ['type','product','dealer','method']).encode()).hexdigest()[:24]


def eligible(payload,state,now):
    current=timestamp(now)
    config=payload['settings']
    if not config['alertEnabled']:return []
    age=current-timestamp(payload['generatedAt'])
    if age < -60 or age > config['maxAgeHours']*3600:raise ValueError('Stale signal export')
    out=[]
    seen=set()
    for signal in payload['signals']:
        if signal.get('excellent') is not True:continue
        age=current-timestamp(signal['observedAt'])
        if age < -60 or age>config['maxAgeHours']*3600:continue
        k=key(signal)
        if k in seen:continue
        seen.add(k)
        previous=state.get(k,{})
        last=previous.get('lastAttemptAt')
        # Pending or uncertain deliveries are suppressed too: avoid duplicate mail.
        if last and current-timestamp(last)<config['cooldownHours']*3600:continue
        out.append(signal)
    return out


def address(value):
    if not value or '\r' in value or '\n' in value:raise ValueError('Invalid email address')
    name,addr=parseaddr(value)
    if addr!=value or '@' not in addr or ',' in addr:raise ValueError('Use one plain email address')
    return addr


def message(signals,sender,recipient,now):
    msg=EmailMessage()
    msg['From']=address(sender);msg['To']=address(recipient)
    msg['Subject']=f'Vivienne — {len(signals)} opportunité(s) à vérifier'
    msg['Date']=formatdate(timestamp(now),localtime=False)
    msg['Message-ID']=make_msgid(domain=sender.split('@')[-1])
    lines=['VIVIENNE · OR & ARGENT','Signaux indicatifs après vos frais et seuils configurés.','']
    for s in signals:
        label={'buy':'Achat','sell':'Vente','spread':'Écart entre boutiques'}[s['type']]
        lines += [f"{label} · {s['product']} · {s['dealer']}",f"Quantité : {s['quantity']} · avantage estimé : {s['edgePct']:.2f} %",f"Observation : {s['observedAt']}",s.get('url',''),'']
    lines += ['Confirmez prix, état, quantité, stock et fiscalité avec la boutique.',
              'Le score mesure un écart historique ou entre boutiques, pas une probabilité de gain.',
              'Les emails utilisent la configuration du dépôt. Vos avoirs privés ne sont pas inclus.']
    msg.set_content('\n'.join(lines))
    return msg


def smtp_send(msg,env=None,smtp_factory=None):
    env=env or os.environ
    host=env.get('SMTP_HOST','');port=int(env.get('SMTP_PORT','587'))
    user,password=env.get('SMTP_USER',''),env.get('SMTP_PASSWORD','')
    if not host or not user or not password:raise ValueError('SMTP credentials are incomplete')
    if port not in (465,587):raise ValueError('Use TLS port 465 or STARTTLS port 587')
    context=ssl.create_default_context()
    factory=smtp_factory or (smtplib.SMTP_SSL if port==465 else smtplib.SMTP)
    kwargs={'timeout':25}
    if port==465:kwargs['context']=context
    with factory(host,port,**kwargs) as smtp:
        smtp.ehlo()
        if port==587:smtp.starttls(context=context);smtp.ehlo()
        smtp.login(user,password)
        refused=smtp.send_message(msg)
        if refused:raise smtplib.SMTPRecipientsRefused(refused)


def deliver(payload,state_path,now,env=None,dry_run=False,send=smtp_send):
    env=env or os.environ;p=Path(state_path)
    state=json.loads(p.read_text()) if p.exists() else {}
    candidates=eligible(payload,state,now)
    if not payload['settings']['alertEnabled']:return {'status':'disabled','count':0,'checkedAt':now}
    if not candidates:return {'status':'no_signal','count':0,'checkedAt':now}
    sender,recipient=env.get('SMTP_FROM',''),env.get('ALERT_TO','')
    if dry_run:
        msg=message(candidates,sender or 'preview@example.invalid',recipient or 'preview@example.invalid',now)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.with_suffix('.preview.eml').write_bytes(bytes(msg))
        return {'status':'dry_run','count':len(candidates),'checkedAt':now}
    if not all(env.get(k) for k in ['SMTP_HOST','SMTP_USER','SMTP_PASSWORD','SMTP_FROM','ALERT_TO']):
        return {'status':'configuration_required','count':0,'checkedAt':now}
    msg=message(candidates,sender,recipient,now)
    for s in candidates:state[key(s)]={'lastAttemptAt':now,'status':'pending'}
    atomic_json(p,state) # Write intent before handing a message to SMTP.
    try:
        send(msg,env)
    except Exception:
        for s in candidates:state[key(s)]['status']='delivery_uncertain'
        atomic_json(p,state)
        raise
    for s in candidates:state[key(s)].update(status='sent',lastSentAt=now)
    atomic_json(p,state)
    return {'status':'sent','count':len(candidates),'checkedAt':now}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--signals',default='private/signals.json');parser.add_argument('--state',default='private/notifications-state.json')
    parser.add_argument('--status',default='data/notifications.json');parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args();now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:
        result=deliver(json.loads(Path(args.signals).read_text()),args.state,now,dry_run=args.dry_run)
    except Exception as error:
        atomic_json(args.status,{'status':'error','count':0,'checkedAt':now})
        # Do not print SMTP exceptions: a provider may echo a private recipient.
        raise SystemExit(f'Notification failed ({type(error).__name__}); inspect provider privately.')
    atomic_json(args.status,result);print(f"Notifications: {result['status']} ({result['count']}).")


if __name__=='__main__':main()
