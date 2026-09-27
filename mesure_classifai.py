# -*- coding: utf-8 -*-
"""Banc de mesure de ClassifAI — les chiffres de la vidéo sortent d'ici.

Le scénario de Gemini annonce des chiffres (20 ms, 100 % de précision,
« facture divisée par 1 000 »…) que personne n'a mesurés. Ce script les
mesure, sur TON PC, avec TON serveur, sur 50 e-mails que ni LAYA ni sa
mémoire n'ont jamais vus.

Ce qu'il mesure
  · LAYA seul, Qwen seul, JEV seul (si tu as une clé), et la cascade
    LAYA → Qwen quand LAYA doute (seuil 45 %, comme l'extension) ;
  · avec 10 classes (une vraie boîte mail) puis avec les 105 classes du
    « Pack Intégral » ;
  · exactitude, exactitude sur les 12 pièges, temps médian et lent (p90),
    part d'e-mails escaladés, réponses « de secours » à mots-clés ;
  · combien de classes Qwen invente pendant le test (il en écrit une dans
    taxonomy.json à CHAQUE appel) ;
  · avec --think : le temps de Qwen avec et sans le <think> pré-fermé.

Ce qu'il ne touche pas
  · il n'envoie aucun feedback : ta mémoire d'apprentissage et les poids
    de LAYA ne bougent pas ;
  · taxonomy.json est sauvegardé au départ et remis en place après chaque
    passe de Qwen, et à la fin même si tu coupes avec Ctrl+C.

Avant : lance le serveur (python server.py dans byGemini\\server) et Ollama.

    python mesure_classifai.py              # tout : ~15 à 30 min selon Qwen
    python mesure_classifai.py --rapide     # LAYA, 10 classes : 1 min, pour vérifier
    python mesure_classifai.py --think      # ajoute le test du <think>
    python mesure_classifai.py --jev-cle sk-...   # ajoute JEV
    python mesure_classifai.py --reprendre  # saute les passes déjà faites

Résultats : resultats_mesure.json (tout, brut) et RESULTATS.md (lisible).
"""
import argparse
import json
import os
import platform
import shutil
import statistics
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, 'resultats_mesure.json')
RAPPORT = os.path.join(ICI, 'RESULTATS.md')
SEUIL = 0.45                      # celui de l'extension (sidepanel.js)

# Pour les 105 classes, certaines réponses voisines sont défendables :
# « souci sur mobile » tombe aussi dans « Accessibilité & Compatibilité ».
# Elles comptent dans le score « tolérant », jamais dans le score strict.
# Le faux changement d'IBAN (m38) n'a PAS d'alternative : le ranger dans
# « Coordonnées Bancaires », c'est exactement l'erreur qui coûte cher.
TOLERE_105 = {
    'm15': ['Accessibilité & Compatibilité'],
    'm20': ['Alerte Monitoring Serveur'],
    'm36': ['Sécurité & Cybermenace'],
    'm39': ['Sécurité & Cybermenace'],
    'm40': ['Sécurité & Cybermenace'],
    'm44': ['Notification Système Automatique'],
}

# Le message que le serveur écrit quand Qwen n'a rien renvoyé d'exploitable
# (délai dépassé, JSON cassé) et qu'il retombe sur des mots-clés.
REPLI_QWEN = "analyse sémantique du sujet et de l'expéditeur"


# ── HTTP, sans dépendance ─────────────────────────────────────────────────
def appel(url, charge=None, delai=120):
    data = None if charge is None else json.dumps(charge).encode('utf-8')
    req = urllib.request.Request(url, data=data,
                                 headers={'Content-Type': 'application/json'})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            rep = json.loads(r.read())
        return rep, (time.perf_counter() - t0) * 1000, None
    except urllib.error.HTTPError as e:
        return None, (time.perf_counter() - t0) * 1000, \
            f'HTTP {e.code} : {e.read().decode("utf-8", "replace")[:300]}'
    except Exception as e:
        return None, (time.perf_counter() - t0) * 1000, str(e)[:300]


def norm(s):
    return (s or '').strip().strip('"').casefold()


# ── les données ───────────────────────────────────────────────────────────
def charger_jeu():
    j = json.load(open(os.path.join(ICI, 'jeu_test.json'), encoding='utf-8'))
    return j['classes'], j['emails']


def charger_pack105(bygemini):
    """Les 105 classes, exactement comme l'extension les envoie : « Nom: description »."""
    p = os.path.join(bygemini, 'extension', 'classes_library.js')
    s = open(p, encoding='utf-8').read()
    lib = json.loads(s[s.index('{'):s.rindex('}') + 1])
    return [f'{k}: {v["description"]}' for k, v in lib.items()]


def avec_description(noms, pack):
    d = {c.split(':')[0].strip(): c for c in pack}
    return [d.get(n, n) for n in noms]


# ── taxonomy.json : sauvegarde / restauration ─────────────────────────────
class Taxonomie:
    def __init__(self, bygemini, reprendre):
        self.f = os.path.join(bygemini, 'server', 'taxonomy.json')
        self.copie = os.path.join(ICI, 'sauvegarde_taxonomy.json')
        # une nouvelle mesure photographie l'état du jour ; une reprise garde
        # la photo de la mesure interrompue (le fichier a pu être sali entre-temps)
        if not (reprendre and os.path.exists(self.copie)):
            shutil.copy2(self.f, self.copie)
        self.cles = set(json.load(open(self.copie, encoding='utf-8')))

    def nouvelles(self):
        try:
            return sorted(set(json.load(open(self.f, encoding='utf-8'))) - self.cles)
        except Exception:
            return []

    def restaurer(self):
        shutil.copy2(self.copie, self.f)


# ── une passe ─────────────────────────────────────────────────────────────
def passe(a, nom, moteur, cascade, classes, emails, tolere, taxo):
    print(f'\n━━ {nom} ━━  ({len(emails)} e-mails, {len(classes)} classes)', flush=True)
    lignes = []
    for i, e in enumerate(emails, 1):
        charge = {
            'engine': moteur, 'subject': e['objet'], 'body': e['corps'],
            'sender': e['expediteur'], 'classes': classes,
            'model_variant': 'multilingual', 'ollama_model': a.qwen,
            'cascade_on_uncertain': cascade, 'uncertainty_threshold': SEUIL,
        }
        if moteur == 'jev':
            charge['jev_api_key'] = a.jev_cle
        rep, mur, err = appel(f'{a.serveur}/classify', charge, delai=180)
        r = rep or {}
        obtenu = r.get('category')
        ok = norm(obtenu) == norm(e['attendu'])
        ok_tol = ok or norm(obtenu) in {norm(x) for x in tolere.get(e['id'], [])}
        crit = r.get('criteria_used')
        candidats = list(crit) if isinstance(crit, dict) else None
        moteur_rep = r.get('engine') or ''
        lignes.append({
            'id': e['id'], 'attendu': e['attendu'], 'obtenu': obtenu,
            'propose': r.get('suggested_category') or r.get('primary_category'),
            'correct': ok, 'correct_tolere': ok_tol, 'piege': bool(e.get('piege')),
            'confiance': r.get('confidence'),
            'confiance_1er': r.get('primary_confidence'),
            'incertain': r.get('is_uncertain'),
            'escalade': bool(r.get('escalated_to_llm')),
            'moteur': moteur_rep,
            'ms_serveur': r.get('elapsed_ms'), 'ms_total': round(mur, 1),
            'candidats': candidats,
            'vraie_dans_candidats': (None if candidats is None
                                     else any(norm(c) == norm(e['attendu']) for c in candidats)),
            'memoire': bool(r.get('is_learned')),
            'repli_mots_cles': ('heuristique' in moteur_rep
                                or REPLI_QWEN in (r.get('explanation') or '')),
            'erreur': err,
        })
        l = lignes[-1]
        marque = '✓' if ok else ('~' if ok_tol else '✗')
        conf = f'{l["confiance"]:.2f}' if isinstance(l['confiance'], (int, float)) else ' -- '
        print(f'  {e["id"]} {marque} {conf} {mur:7.0f} ms  {str(obtenu)[:38]:38s}'
              + ('  ⇢ Qwen' if l['escalade'] else '')
              + (f'  [ERREUR {err[:60]}]' if err else ''), flush=True)
    if taxo:
        nv = taxo.nouvelles()
        taxo.restaurer()
        print(f'  classes ajoutées à taxonomy.json pendant la passe : {len(nv)} (remis en état)')
        return {'lignes': lignes, 'classes_inventees': nv}
    return {'lignes': lignes, 'classes_inventees': []}


# ── le test du <think> ────────────────────────────────────────────────────
def prompt_serveur(e, noms, preferme):
    """Le prompt de server.py, avec ou sans la balise <think> déjà fermée."""
    tete = (f"<system>Tu es un classificateur d'e-mails professionnel. Tu réponds STRICTEMENT "
            f"par un objet JSON valide, sans texte d'introduction ni bavardage.</system>\n"
            f"Analyse l'e-mail suivant et attribue-lui sa catégorie précise en français "
            f"(1 à 3 mots, ex: Factures, Support, Devis, RH, Commercial, Urgent, etc.) :\n\n"
            f"Expéditeur : {e['expediteur']}\nObjet : {e['objet']}\nCorps de l'e-mail :\n"
            f"{e['corps']}\n\nCatégories possibles recommandées : {', '.join(noms)}.\n")
    if preferme:
        return tete + '\n<think>\nAnalyse synthétique : intention identifiée.\n</think>\n{\n  "category":'
    return tete + '\nRéponds avec un objet JSON {"category": "..."}.'


def test_think(a, emails, noms):
    choix = [e for e in emails if e['id'] in ('m01', 'm11', 'm17', 'm38', 'm47')]
    modes = [
        ('reflexion_libre', False, {}),
        ('think_preferme', True, {}),               # l'astuce de server.py
        ('think_false', False, {'think': False}),   # le réglage officiel d'Ollama
    ]
    res = {}
    for nom, preferme, extra in modes:
        print(f'\n━━ Qwen · {nom} ━━', flush=True)
        lignes = []
        for e in choix:
            charge = {'model': a.qwen, 'prompt': prompt_serveur(e, noms, preferme),
                      'stream': False,
                      'options': {'temperature': 0.1,
                                  'num_predict': 512 if preferme else 4096}}
            if preferme:
                charge['format'] = 'json'
            charge.update(extra)
            rep, mur, err = appel(f'{a.ollama}/api/generate', charge, delai=400)
            r = rep or {}
            texte = (r.get('response') or '')
            lignes.append({'id': e['id'], 'attendu': e['attendu'], 'ms': round(mur),
                           'jetons': r.get('eval_count'),
                           'jetons_reflexion_car': len(r.get('thinking') or ''),
                           'reponse': texte[-160:], 'erreur': err})
            print(f'  {e["id"]} {mur / 1000:6.1f} s  {r.get("eval_count")} jetons  '
                  f'{texte.strip()[-60:]!r}' + (f'  [ERREUR {err[:60]}]' if err else ''),
                  flush=True)
        res[nom] = lignes
    return res


# ── le rapport ────────────────────────────────────────────────────────────
def pct(n, d):
    return f'{100 * n / d:.0f} %' if d else '—'


def ms(v):
    if v is None:
        return '—'
    return f'{v:.0f} ms' if v < 1000 else f'{v / 1000:.1f} s'


def resume(bloc):
    L = [l for l in bloc['lignes'] if not l['erreur']]
    n = len(L)
    t = sorted(l['ms_total'] for l in L)
    p = [l for l in L if l['piege']]
    cand = [l for l in L if l['vraie_dans_candidats'] is not None]
    return {
        'n': n, 'erreurs': len(bloc['lignes']) - n,
        'justes': sum(l['correct'] for l in L),
        'justes_tol': sum(l['correct_tolere'] for l in L),
        'pieges': len(p), 'pieges_justes': sum(l['correct'] for l in p),
        'mediane_ms': statistics.median(t) if t else None,
        'p90_ms': t[min(len(t) - 1, int(0.9 * len(t)))] if t else None,
        'total_s': sum(t) / 1000,
        'escalades': sum(l['escalade'] for l in L),
        'incertains': sum(bool(l['incertain']) for l in L),
        'repli': sum(l['repli_mots_cles'] for l in L),
        'memoire': sum(l['memoire'] for l in L),
        'dans_candidats': (sum(l['vraie_dans_candidats'] for l in cand), len(cand)),
        'inventees': len(bloc['classes_inventees']),
    }


def rapport(res):
    m = res['machine']
    o = ['# Résultats du banc ClassifAI', '',
         f'Mesuré le {res["date"]} · {m["gpu"]} · Qwen : `{m["qwen"]}` · '
         f'50 e-mails inédits, dont 12 pièges.', '',
         '| Passe | Justes | Pièges | Temps médian | Lent (p90) | 50 e-mails | Escaladés | Repli mots-clés |',
         '|---|---|---|---|---|---|---|---|']
    for nom, bloc in res['passes'].items():
        s = resume(bloc)
        juste = f'{s["justes"]}/{s["n"]}'
        if s['justes_tol'] != s['justes']:
            juste += f' (tolérant {s["justes_tol"]})'
        o.append(f'| {nom} | {juste} | {s["pieges_justes"]}/{s["pieges"]} | '
                 f'{ms(s["mediane_ms"])} | {ms(s["p90_ms"])} | {s["total_s"]:.0f} s | '
                 f'{s["escalades"] or "—"} | {s["repli"] or "—"} |')
    o += ['', '## Ce qu’il faut regarder', '']
    for nom, bloc in res['passes'].items():
        s = resume(bloc)
        bits = []
        if s['dans_candidats'][1]:
            a, b = s['dans_candidats']
            bits.append(f'la bonne classe était dans les 8 présélectionnées pour {a}/{b} e-mails')
        if s['inventees']:
            bits.append(f'Qwen a créé **{s["inventees"]} classes** dans taxonomy.json '
                        f'(ex. {", ".join(bloc["classes_inventees"][:5])})')
        if s['memoire']:
            bits.append(f'⚠ {s["memoire"]} réponses venaient de la mémoire, pas du modèle')
        if s['repli']:
            bits.append(f'⚠ {s["repli"]} réponses de secours à mots-clés')
        if s['erreurs']:
            bits.append(f'⚠ {s["erreurs"]} erreurs')
        if bits:
            o.append(f'- **{nom}** : ' + ' ; '.join(bits) + '.')
    if res.get('think'):
        o += ['', '## Le <think> de Qwen', '', '| Mode | Temps moyen | Jetons moyens |', '|---|---|---|']
        for mode, L in res['think'].items():
            ok = [l for l in L if not l['erreur']]
            if ok:
                o.append(f'| {mode} | {statistics.mean(l["ms"] for l in ok) / 1000:.1f} s | '
                         f'{statistics.mean((l["jetons"] or 0) for l in ok):.0f} |')
            else:
                o.append(f'| {mode} | erreur : {L[0]["erreur"][:60]} | — |')
    o += ['', '## Les erreurs, une par une', '']
    for nom, bloc in res['passes'].items():
        faux = [l for l in bloc['lignes'] if not l['correct'] and not l['erreur']]
        if faux:
            o.append(f'**{nom}**')
            o += [f'- {l["id"]} attendu *{l["attendu"]}* → **{l["obtenu"]}**'
                  + (f' (conf. {l["confiance"]:.2f})' if isinstance(l['confiance'], (int, float)) else '')
                  + (' · piège' if l['piege'] else '') for l in faux]
            o.append('')
    open(RAPPORT, 'w', encoding='utf-8').write('\n'.join(o) + '\n')


# ── main ──────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--serveur', default='http://127.0.0.1:8000')
    ap.add_argument('--ollama', default='http://127.0.0.1:11434')
    ap.add_argument('--qwen', default='qwen3.5:latest')
    ap.add_argument('--bygemini', default=os.path.join(ICI, '..', '..', 'byGemini'))
    ap.add_argument('--jev-cle', default=os.environ.get('TYPESAFE_API_KEY'))
    ap.add_argument('--rapide', action='store_true')
    ap.add_argument('--think', action='store_true')
    ap.add_argument('--reprendre', action='store_true')
    a = ap.parse_args()
    a.bygemini = os.path.abspath(a.bygemini)

    noms, emails = charger_jeu()
    pack = charger_pack105(a.bygemini)
    c10 = avec_description(noms, pack)

    sante, _, err = appel(f'{a.serveur}/health', delai=10)
    if err:
        sys.exit(f'Le serveur ne répond pas sur {a.serveur} ({err}).\n'
                 f'Lance-le d’abord : cd byGemini\\server puis python server.py')
    gpu = sante.get('torch', {}).get('device', '?')
    modeles = sante.get('ollama', {}).get('models', [])
    print(f'Serveur OK · {gpu} · Ollama : {", ".join(modeles) or "absent"}')

    res = {'date': time.strftime('%Y-%m-%d %H:%M'),
           'machine': {'gpu': gpu, 'os': platform.platform(), 'cpu': platform.processor(),
                       'qwen': a.qwen, 'ollama_modeles': modeles},
           'passes': {}}
    if a.reprendre and os.path.exists(SORTIE):
        res = json.load(open(SORTIE, encoding='utf-8'))

    # échauffement : le 1er appel charge LAYA (et Qwen) en mémoire, il ne compte pas
    essai = {'subject': 'Bonjour', 'body': 'Message de test pour le chargement.',
             'sender': 'test@exemple.fr', 'classes': c10, 'ollama_model': a.qwen}
    print('Chargement de LAYA…', flush=True)
    r, t, err = appel(f'{a.serveur}/classify', dict(essai, engine='laya'), delai=600)
    if err or 'heuristique' in (r or {}).get('engine', ''):
        sys.exit(f'LAYA ne répond pas avec le vrai modèle ({err or r.get("engine")}).\n'
                 f'Les chiffres seraient ceux du repli à mots-clés : on s’arrête là.')
    print(f'  prêt ({t / 1000:.1f} s)')

    qwen_ok = a.qwen in modeles or any(m.split(':')[0] == a.qwen.split(':')[0] for m in modeles)
    jev_ok = bool(a.jev_cle)
    plan = [('LAYA · 10 classes', 'laya', False, c10, {})]
    if not a.rapide:
        plan += [('LAYA · 105 classes', 'laya', False, pack, TOLERE_105)]
        if qwen_ok:
            plan += [('Qwen · 10 classes', 'ollama', False, c10, {}),
                     ('Qwen · 105 classes', 'ollama', False, pack, TOLERE_105),
                     ('LAYA → Qwen · 10 classes', 'laya', True, c10, {}),
                     ('LAYA → Qwen · 105 classes', 'laya', True, pack, TOLERE_105)]
        else:
            print(f'⚠ {a.qwen} absent d’Ollama : passes Qwen et cascade sautées.')
        if jev_ok:
            plan += [('JEV · 10 classes', 'jev', False, c10, {}),
                     ('JEV · 105 classes', 'jev', False, pack, TOLERE_105)]
        else:
            print('· pas de clé JEV : passes JEV sautées (--jev-cle pour les ajouter).')

    taxo = Taxonomie(a.bygemini, a.reprendre)
    try:
        if qwen_ok and not a.rapide:
            print('Chargement de Qwen…', flush=True)
            _, t, _ = appel(f'{a.serveur}/classify', dict(essai, engine='ollama'), delai=600)
            taxo.restaurer()
            print(f'  prêt ({t / 1000:.1f} s)')
        for nom, moteur, cascade, classes, tol in plan:
            if a.reprendre and nom in res['passes']:
                print(f'\n━━ {nom} ━━ déjà fait')
                continue
            ecrit = moteur == 'ollama' or cascade
            res['passes'][nom] = passe(a, nom, moteur, cascade, classes, emails, tol,
                                       taxo if ecrit else None)
            json.dump(res, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            rapport(res)
        if a.think and qwen_ok:
            res['think'] = test_think(a, emails, noms)
            json.dump(res, open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            rapport(res)
    finally:
        taxo.restaurer()
        print('\ntaxonomy.json remis dans son état de départ.')

    print(f'\n→ {RAPPORT}\n→ {SORTIE}')
    print(open(RAPPORT, encoding='utf-8').read().split('## Les erreurs')[0])


if __name__ == '__main__':
    main()
