import copy
import json
from pathlib import Path
import tempfile
import unittest
from collector.notify import eligible,deliver,message,smtp_send,key,address

NOW='2026-09-21T14:00:00+00:00'
SIGNAL={'type':'buy','product':'coq20','dealer':'test-dealer','method':'test','excellent':True,'observedAt':NOW,'quantity':1,'edgePct':2.4,'url':'https://example.org/coin'}
PAYLOAD={'generatedAt':NOW,'settings':{'alertEnabled':True,'maxAgeHours':6,'cooldownHours':24},'signals':[SIGNAL]}
ENV={'SMTP_HOST':'smtp.example.invalid','SMTP_PORT':'587','SMTP_USER':'test','SMTP_PASSWORD':'test-password','SMTP_FROM':'sender@example.invalid','ALERT_TO':'recipient@example.invalid'}


class NotificationTests(unittest.TestCase):
    def test_disabled(self):
        p=copy.deepcopy(PAYLOAD);p['settings']['alertEnabled']=False
        self.assertEqual(eligible(p,{},NOW),[])
    def test_cooldown_independent_of_quote_price(self):
        state={key(SIGNAL):{'lastAttemptAt':NOW,'status':'sent'}}
        p=copy.deepcopy(PAYLOAD);p['signals'][0]['price']=123456
        self.assertEqual(eligible(p,state,'2026-09-21T15:00:00+00:00'),[])
    def test_rearm_after_cooldown(self):
        state={key(SIGNAL):{'lastAttemptAt':'2026-09-20T13:00:00+00:00','status':'sent'}}
        self.assertEqual(len(eligible(PAYLOAD,state,NOW)),1)
    def test_stale_export(self):
        self.assertRaises(ValueError,eligible,PAYLOAD,{},'2026-09-22T14:00:00+00:00')
    def test_stale_signal_and_nonexcellent(self):
        p=copy.deepcopy(PAYLOAD);p['signals'][0]['observedAt']='2026-09-20T14:00:00+00:00'
        self.assertEqual(eligible(p,{},NOW),[])
        p=copy.deepcopy(PAYLOAD);p['signals'][0]['excellent']=False
        self.assertEqual(eligible(p,{},NOW),[])
    def test_duplicate_signals(self):
        p=copy.deepcopy(PAYLOAD);p['signals']*=2
        self.assertEqual(len(eligible(p,{},NOW)),1)
    def test_dry_run_does_not_send_or_consume_state(self):
        with tempfile.TemporaryDirectory() as d:
            state=d+'/state.json'
            result=deliver(PAYLOAD,state,NOW,ENV,True,send=lambda *_:self.fail('send called'))
            self.assertEqual(result['status'],'dry_run');self.assertFalse(Path(state).exists())
            self.assertIn('test-dealer',Path(d+'/state.preview.eml').read_text())
    def test_success_then_idempotent_retry(self):
        with tempfile.TemporaryDirectory() as d:
            sent=[];state=d+'/state.json'
            result=deliver(PAYLOAD,state,NOW,ENV,send=lambda msg,env:sent.append(msg))
            self.assertEqual(result['status'],'sent')
            self.assertEqual(deliver(PAYLOAD,state,NOW,ENV,send=lambda *_:self.fail('duplicate'))['status'],'no_signal')
            self.assertEqual(len(sent),1);self.assertEqual(sent[0]['To'],ENV['ALERT_TO'])
    def test_failure_records_uncertainty_and_suppresses_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            def fail(*_):raise OSError('connection lost after DATA')
            self.assertRaises(OSError,deliver,PAYLOAD,d+'/state.json',NOW,ENV,False,fail)
            state=json.loads(Path(d+'/state.json').read_text())
            self.assertEqual(state[key(SIGNAL)]['status'],'delivery_uncertain')
            self.assertEqual(eligible(PAYLOAD,state,NOW),[])
    def test_missing_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(deliver(PAYLOAD,d+'/state.json',NOW,{'SMTP_HOST':'x'})['status'],'configuration_required')
    def test_header_injection(self):
        self.assertRaises(ValueError,address,'me@example.org\nBcc: somebody@example.org')
        self.assertRaises(ValueError,address,'a@example.org,b@example.org')
    def test_tls_before_authentication(self):
        events=[]
        class SMTP:
            def __init__(self,*args,**kwargs):events.append('connect')
            def __enter__(self):return self
            def __exit__(self,*args):events.append('close')
            def ehlo(self):events.append('ehlo')
            def starttls(self,context):self.assert_context=context;events.append('tls')
            def login(self,*args):events.append('login')
            def send_message(self,msg):events.append('send');return {}
        smtp_send(message([SIGNAL],ENV['SMTP_FROM'],ENV['ALERT_TO'],NOW),ENV,SMTP)
        self.assertEqual(events,['connect','ehlo','tls','ehlo','login','send','close'])
    def test_plaintext_port_rejected(self):
        env={**ENV,'SMTP_PORT':'25'}
        self.assertRaises(ValueError,smtp_send,message([SIGNAL],ENV['SMTP_FROM'],ENV['ALERT_TO'],NOW),env)


if __name__=='__main__':unittest.main()
