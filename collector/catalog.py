"""Exact observed labels. No fuzzy matching of weights, metals or effigies."""
ALIASES = {
 'napoleon20': ['20 Francs Napoleon','20 F Napoleon','20 Frs Napoleon',"Achat 20 Francs Napoléon dit Louis d’Or"],
 'coq20': ['20 Francs Or Napoléon type Coq','20 Francs Napoléon type Coq Or',"Pièce d’Or 20 Francs Coq Marianne"],
 'napoleon10': ['10 Francs Napoleon',"Pièce d’Or 10 Francs Napoléon"],
 'coq10': ['10 Francs Or COQ','10 Francs Coq Or'],
 'swiss20': ['20 Francs Croix Suisse','20 Francs Suisse','20 F Suisse','20 Frs Croix Suisse','20 Francs Or Suisse','20 Francs Suisse Or',"Pièce d’Or 20 Francs Suisse"],
 'latin20': ['20 Francs Union Latine','20 F Union Latine','20 Frs Union Latine','Union Latine','Union Latine Or','20 Francs Union Latine Or'],
 'tunisia20': ['20 Francs Tunisie',"Pièce d’Or 20 Francs Tunisie"],
 'sovereign': ['Souverain',"Pièce d’Or Souverain"],
 'sovereigngeorge': ['Souverain Or Georges','Souverains Georges Or'],
 'sovereignelizabeth': ['Souverain Elizabeth','Souverain Elizabeth II','Souverain Elisabeth II Or','Souverain Elisabeth II','Souverain Elisabeth',"Pièce d’Or Souverain Elizabeth II"],
 'halfsovereign': ['1/2 Souverain','1/2 Souverain Or','Demi Souverain'],
 'usd20': ['20 Dollars','20 Dollars Or','20 Dollars US','20 $ US',"Pièce d’Or 20 Dollars US"],
 'usd10': ['10 Dollars','10 Dollars Or','10 Dollars US','10 $ US','Dollars 10'],
 'usd10liberty': ["Pièce d’Or 10 Dollars Liberty"], 'usd10indian': ["Pièce d’Or 10 Dollars Tête d’Indien"],
 'usd5': ['5 Dollars','5 Dollars Or','5 Dollars US Or','5 $ US',"Pièce d’Or 5 Dollars US"],
 'pesos50': ['50 Pesos','50 Pesos Or','50 Pesos Mexique','50 Pesos Or Mexique',"Pièce d’Or 50 Pesos Mexicain"],
 'florins10': ['10 Florins','10 Florins Or','10 Florins Hollandais','10 Florins Or Hollandais',"Pièce d’Or 10 Florins – 10 Gulden"],
 'marks20': ['20 Marks Or','20 Deutsch Marks','20 Reichsmarks','20 Reichsmark'],
 'roubles5': ['5 Roubles'], 'krugerrand': ['Krugerrand','Krugerrand Or Afrique du Sud','Krugerrand Afrique du Sud Or',"Pièce d’Or Krugerrand"],
 'maplegold': ['Maple Leaf 1 Once Or Canada'], 'eaglegold': ['American Eagle 1 Once Or'],
 'buffalogold': ['Buffalo 1 Once Or Etats Unis'], 'philharmonicgold': ['Philharmonique 1 Once Or Autriche'], 'kangaroogold': ['Kangourou 1 Once Or Australie'],
 'hercule50': ['50 Francs Hercule Argent','50 Francs Argent Hercule','50 Francs Hercule 1974 - 1980','50 Frs Hercule (1974-1980)'],
 'hercule10': ['10 Francs Hercule Argent','10 Francs Argent Hercule','10 Francs Hercule 1964 - 1973','10 Frs Hercule (1964-1973)'],
 'semeuse5': ['5 Francs Argent Semeuse','5 Francs Semeuse 1959-1969','5 Frs Semeuse (1959-1969)'],
 'semeuse2': ['2 Francs Semeuse','2 Francs Argent Semeuse','2 Frs Semeuse (1898-1920)'],
 'semeuse1': ['1 Franc Semeuse','1 Franc Argent Semeuse','1 Fr Semeuse (1898-1920)'],
 'semeuse050': ['50 Centimes Semeuse','50 Centimes Argent Semeuse','0,50 Fr Semeuse (1897-1920)'],
 'ecu5': ['5 Francs Ecu 3 Têtes','5 Francs ECU (3 TETES) argent'],
 'turin20': ['20 Francs Turin Argent','20 Francs Argent Turin','20 Frs Turin (1929-1939)'],
 'turin10': ['10 Francs Turin Argent','10 Francs Argent Turin','10 Frs Turin (1929-1939)'],
 'francs100silver': ['100 Francs Argent tous modèles','100 Francs tous modèles','100 Francs Argent'],
 'maplesilver': ['Once Argent Maple Leaf Canada',"Once d'Argent Canada Maple Leaf",'Maple Leaf 1 Once Argent'],
 'eaglesilver': ["Once d'Argent USA",'Silver Eagle 1 Once'],
 'philharmonicsilver': ['Once Argent Autriche'], 'krugerrandsilver': ['Krugerrand 1 Once Argent'],
 'goldoz': ['Lingotin Once Or','Lingotin once CPoR','Once CPoR',"Lingot d’or 1 Once Or (soit 31,1 gramme)"],
 'gold1000': ['Lingot','Lingot 1 kg','Lingot 1Kg Or','Lingot Or 1 kg','Achat Lingot or 1 kg'],
}
for grams in (1,2,5,10,20,50,100,250,500):
 ALIASES[f'gold{grams}'] = [f'{a} {grams}{b}' for a in ('Lingotin','Lingot') for b in ('g Or','g','g CPoR',' Gr CPoR')] + [f'{a} Or {grams} {b}' for a in ('Lingotin','Lingot') for b in ('grammes','Gr','g','Gramme')]
for grams in (100,250,500,1000,5000):
 ALIASES[f'silver{grams}'] = [f'{a} Argent {grams} {b}' for a in ('Lingot','Lingotin') for b in ('grammes','GR')] + [f'Lingot {grams}g Argent']
ALIASES['silver1000'] += ['Lingot Argent 1 KG','Lingot 1 Kilo Argent']
ALIASES['silver5000'] += ['Lingot Argent 5 KG']

ALIASES['goldoz'] += ['Lingotin 31,10 Gr (Oz)']
ALIASES['ecu5'] += ['5 Frs Ecu (1795-1889)']
ALIASES['francs100silver'] += ['100 Frs (1982-2002)']
