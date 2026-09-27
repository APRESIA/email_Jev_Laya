# -*- coding: utf-8 -*-
"""JEV sur le même banc : 50 e-mails, 10 puis 105 catégories.

Exactement ce que fait classify_with_jev dans server.py (mêmes définitions de
classes, même question, même SDK TypeSafe), sans la mémoire
d'auto-apprentissage : on mesure le modèle, pas le cache.

La clé n'est jamais écrite ni affichée. Deux façons de la donner :

    set TYPESAFE_API_KEY=ta_cle          (Windows, dans la même fenêtre)
    python jev.py

ou bien laisse le script la demander (la saisie est masquée) :

    python jev.py

100 appels en tout. Au prix annoncé par TypeSafe (0,0004 $ par décision),
c'est environ 4 centimes de dollar.

Résultats : JEV.md et jev_resultats.json, à côté de ce script.
"""
import getpass
import json
import os
import statistics
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ICI = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.abspath(os.path.join(ICI, '..', '..', 'byGemini', 'server'))
sys.path.insert(0, ICI)
from mesure_classifai import TOLERE_105, avec_description, charger_jeu, charger_pack105, norm  # noqa: E402

INSTR = "Classe cet e-mail dans la catégorie appropriée selon son contenu."


def passe(client, Choice, srv, nom, classes, emails, tolere):
    criteria, noms = srv.parse_and_enrich_classes(classes)
    print(f'\n━━ {nom} ━━', flush=True)
    L = []
    for e in emails:
        state = (f"Expéditeur: {e['expediteur']}\nObjet: {e['objet']}\n"
                 f"Fil de discussion et historique complet:\n{e['corps']}")
        t0 = time.perf_counter()
        err, choix, conf = None, None, None
        try:
            rep = client.system_one(state=state, questions={
                'category': Choice(instructions=INSTR, criteria=criteria)})
            a = rep.answers['category']
            choix = getattr(a, 'answer', None) or getattr(a, 'choice', None)
            c = getattr(a, 'confidence', None)
            conf = float(c) if isinstance(c, (int, float)) else None
        except Exception as x:
            err = str(x)[:200]
        dt = (time.perf_counter() - t0) * 1000
        ok = norm(choix) == norm(e['attendu'])
        L.append({'id': e['id'], 'attendu': e['attendu'], 'obtenu': choix, 'correct': ok,
                  'correct_tolere': ok or norm(choix) in {norm(x) for x in tolere.get(e['id'], [])},
                  'piege': bool(e.get('piege')), 'confiance': conf, 'ms': round(dt, 1),
                  'erreur': err})
        cf = f'{conf:.2f}' if conf is not None else ' -- '
        print(f"  {e['id']} {'✓' if ok else '✗'} {cf} {dt:6.0f} ms  {str(choix)[:40]}"
              + (f'  [ERREUR {err[:60]}]' if err else ''), flush=True)
        if err and len(L) <= 2 and all(l['erreur'] for l in L):
            sys.exit('Les deux premiers appels échouent : clé refusée ou API injoignable.\n' + err)
    return L


def main():
    cle = os.environ.get('TYPESAFE_API_KEY') or getpass.getpass('Clé TypeSafe JEV (masquée) : ').strip()
    if not cle:
        sys.exit('Pas de clé.')
    noms, emails = charger_jeu()
    pack = charger_pack105(os.path.join(SERVEUR, '..'))
    c10 = avec_description(noms, pack)

    sys.path.insert(0, SERVEUR)
    os.chdir(SERVEUR)
    import server as srv
    from typesafe_sdk import Choice, TypeSafeClient
    client = TypeSafeClient(api_key=cle)

    res = {'date': time.strftime('%Y-%m-%d %H:%M'), 'passes': {}}
    res['passes']['JEV · 10 classes'] = passe(client, Choice, srv, 'JEV · 10 classes', c10, emails, {})
    res['passes']['JEV · 105 classes'] = passe(client, Choice, srv, 'JEV · 105 classes', pack, emails, TOLERE_105)
    json.dump(res, open(os.path.join(ICI, 'jev_resultats.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    o = ['# JEV sur le banc', '', f'Mesuré le {res["date"]} · 50 e-mails, 12 pièges.', '',
         '| Passe | Justes | Pièges | Médian | Lent (p90) | Faux à ≥ 90 % | Erreurs API |', '|---|---|---|---|---|---|---|']
    for nom, L in res['passes'].items():
        ok = [l for l in L if not l['erreur']]
        t = sorted(l['ms'] for l in ok) or [0]
        p = [l for l in ok if l['piege']]
        j = sum(l['correct'] for l in ok)
        tol = sum(l['correct_tolere'] for l in ok)
        f90 = sum(1 for l in ok if not l['correct'] and (l['confiance'] or 0) >= 0.9)
        o.append(f"| {nom} | {j}/{len(L)}" + (f" (tolérant {tol})" if tol != j else '') +
                 f" | {sum(l['correct'] for l in p)}/{len(p)} | {statistics.median(t):.0f} ms | "
                 f"{t[min(len(t) - 1, int(.9 * len(t)))]:.0f} ms | {f90} | {len(L) - len(ok)} |")
    o += ['', '## Erreurs', '']
    for nom, L in res['passes'].items():
        o.append(f'**{nom}**')
        o += [f"- {l['id']} attendu *{l['attendu']}* → **{l['obtenu']}**"
              + (f" ({l['confiance']:.2f})" if l['confiance'] is not None else '')
              + (' · piège' if l['piege'] else '') for l in L if not l['correct'] and not l['erreur']]
        o.append('')
    open(os.path.join(ICI, 'JEV.md'), 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    print('\n' + '\n'.join(o[:8]))


if __name__ == '__main__':
    main()
