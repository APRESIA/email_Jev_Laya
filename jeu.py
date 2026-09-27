# -*- coding: utf-8 -*-
"""Le jeu de test du banc : 50 e-mails inédits, 10 classes, 5 par classe.

Règles d'écriture :
  · aucun de ces e-mails n'est dans continual_dataset.json ni dans les
    exemples de taxonomy.json — sinon la « mémoire » répondrait à la place
    du modèle et on mesurerait une recherche, pas une classification ;
  · chaque classe a au moins un piège (marqué `piege`), qui ressemble à une
    classe voisine : un bug gênant n'est pas une panne P0, un devis n'est pas
    une facture, un faux mail de facture est une fraude ;
  · les noms de classes sont exactement ceux de la bibliothèque de
    l'extension, pour que LAYA profite de ses définitions comme en vrai.

    python jeu.py      # écrit jeu_test.json
"""
import json

CLASSES = [
    'Demande de Devis',
    'Facture Fournisseur',
    'Bug Logiciel',
    'Incident Bloquant / P0',
    'Candidature Spontanée',
    'Demande de Congés & Absence',
    'Newsletter & Veille Sectorielle',
    'Tentative de Fraude / Hameçonnage',
    'Invitation Réunion Calendrier',
    'Suivi de Livraison & Tracking',
]

# (classe, expéditeur, objet, corps, piège ou None)
E = [
    # ── Demande de Devis ──────────────────────────────────────────────────
    ('Demande de Devis', 'achats@menuiserie-roux.fr',
     'Tarif pour 12 postes',
     "Bonjour,\nNous équipons notre nouvel atelier et cherchons une solution pour 12 postes. "
     "Pouvez-vous nous indiquer vos prix, avec et sans l'option de sauvegarde ?\nMerci,\nClaire Roux", None),
    ('Demande de Devis', 'j.benali@cabinet-benali.fr',
     'Accompagnement migration',
     "Bonjour, nous aimerions être accompagnés pour migrer nos données vers votre plateforme. "
     "Combien coûterait une prestation de deux jours sur site à Lyon ? Merci de nous faire une proposition chiffrée.", None),
    ('Demande de Devis', 'direction@ecole-les-tilleuls.fr',
     'Question sur vos tarifs éducation',
     "Madame, Monsieur, existe-t-il un tarif réduit pour les établissements scolaires ? "
     "Nous aurions besoin d'environ 40 comptes enseignants à la rentrée. Pouvez-vous nous envoyer une estimation ?", None),
    ('Demande de Devis', 'p.martin@logistique-martin.com',
     'Re: votre facture de mars',
     "Merci pour la facture de mars, elle est bien passée en paiement. "
     "Par ailleurs nous voulons ajouter 3 entrepôts l'an prochain : pouvez-vous nous chiffrer cette extension "
     "avant la fin du mois ?",
     "mot « facture » dans l'objet, mais la demande est un chiffrage"),
    ('Demande de Devis', 'contact@studio-ocre.fr',
     'Projet site vitrine',
     "Hello ! On refait notre site et on voudrait savoir dans quelle fourchette de prix vous êtes "
     "pour une maquette + intégration, 6 pages. Budget serré mais on est flexibles sur le délai.", None),

    # ── Facture Fournisseur ───────────────────────────────────────────────
    ('Facture Fournisseur', 'facturation@hebergement-nordik.eu',
     'Votre facture n° NK-88214',
     "Bonjour,\nVeuillez trouver ci-joint la facture NK-88214 d'un montant de 312,00 € HT pour "
     "l'hébergement du mois de septembre. Échéance : 30 jours.\nService facturation", None),
    ('Facture Fournisseur', 'compta@imprimerie-delorme.fr',
     'Impression plaquettes – facture',
     "Suite à la livraison des 2 000 plaquettes, voici notre facture. Le règlement est attendu "
     "par virement à réception. Nos coordonnées bancaires n'ont pas changé.", None),
    ('Facture Fournisseur', 'no-reply@telecom-pro.fr',
     'Votre facture mobile est disponible',
     "Votre facture professionnelle de 18 lignes est disponible dans votre espace client. "
     "Montant : 486,40 € TTC. Prélèvement le 12.", None),
    ('Facture Fournisseur', 'admin@cabinet-expertise-leroy.fr',
     'Honoraires T3',
     "Bonjour, ci-joint notre note d'honoraires pour le troisième trimestre (bilan intermédiaire "
     "et déclarations). Merci de votre confiance.", None),
    ('Facture Fournisseur', 'ventes@fournitures-bureau-plus.fr',
     'Votre commande 55102 – document comptable',
     "Votre commande de fournitures a été expédiée. Le document comptable correspondant (facture "
     "F-55102, 129,90 € HT) est joint à ce message.",
     "parle aussi d'expédition, mais l'objet du mail est la facture"),

    # ── Bug Logiciel ──────────────────────────────────────────────────────
    ('Bug Logiciel', 'sophie.garnier@client-agence.fr',
     "L'export PDF coupe les tableaux",
     "Bonjour, quand j'exporte un rapport en PDF, la dernière colonne des tableaux est coupée. "
     "Ça marche bien en Excel. Pas urgent, mais c'est gênant pour nos clients.", None),
    ('Bug Logiciel', 'marc@startup-velo.io',
     'Les accents deviennent des ?',
     "Depuis la dernière mise à jour, les noms avec accents s'affichent avec des « ? » dans les "
     "notifications. Exemple : « H?l?ne ». Le reste fonctionne.", None),
    ('Bug Logiciel', 'l.nguyen@cabinet-medical-sud.fr',
     'Bouton enregistrer grisé',
     "Sur la fiche patient, le bouton Enregistrer reste grisé si on modifie seulement le téléphone. "
     "On contourne en modifiant un autre champ puis en le remettant.", None),
    ('Bug Logiciel', 'it@transports-michaud.fr',
     'URGENT : mauvais tri des colonnes',
     "Le tri par date dans la liste des tournées trie par jour au lieu de trier par date complète "
     "(le 02/11 passe avant le 28/10). Les équipes s'en sortent en filtrant à la main.",
     "« URGENT » dans l'objet, mais rien n'est bloqué : contournement possible"),
    ('Bug Logiciel', 'anais@boutique-lin.fr',
     'Petit souci sur mobile',
     "Sur iPhone, le menu du haut chevauche le titre de la page quand on tourne l'écran. "
     "Sur Android c'est bon.", None),

    # ── Incident Bloquant / P0 ────────────────────────────────────────────
    ('Incident Bloquant / P0', 'astreinte@pharmacie-centrale.fr',
     'Plus aucun accès depuis 8h',
     "Plus personne ne peut se connecter depuis 8h ce matin, toutes les agences sont à l'arrêt. "
     "Nous ne pouvons plus délivrer d'ordonnances. Merci de rappeler immédiatement au 04 xx.", None),
    ('Incident Bloquant / P0', 'dsi@groupe-hotelier-azur.com',
     'Paiements refusés sur tout le site',
     "Depuis 20 minutes, 100 % des paiements en ligne échouent avec une erreur 500. "
     "Nous perdons toutes les réservations. Escalade demandée.", None),
    ('Incident Bloquant / P0', 'ops@logisticien-est.fr',
     'Synchronisation stoppée – entrepôt à l’arrêt',
     "La synchronisation des commandes est arrêtée, les préparateurs n'ont plus aucune liste. "
     "300 colis doivent partir avant 14h. Quelqu'un peut-il intervenir ?", None),
    ('Incident Bloquant / P0', 'k.dupont@mairie-saint-aubin.fr',
     'Petite question sur la plateforme',
     "Bonjour, depuis ce matin plus aucun agent n'arrive à ouvrir l'application, le guichet "
     "d'état civil est fermé et la file d'attente s'allonge. Que devons-nous faire ?",
     "objet anodin, contenu de panne totale"),
    ('Incident Bloquant / P0', 'noc@fibre-ouest.net',
     'Base de données inaccessible',
     "Alerte : la base de production ne répond plus, toutes les API renvoient des timeouts. "
     "Impact : l'ensemble des clients. Pas de contournement.", None),

    # ── Candidature Spontanée ─────────────────────────────────────────────
    ('Candidature Spontanée', 'yanis.haddad@gmail.com',
     'Candidature – développeur front-end',
     "Bonjour, développeur front-end depuis 4 ans, je suis votre produit depuis longtemps et "
     "j'aimerais rejoindre votre équipe. Vous trouverez mon CV en pièce jointe.", None),
    ('Candidature Spontanée', 'lea.moreau@outlook.fr',
     'Proposition de collaboration',
     "Madame, Monsieur, comptable de formation, je souhaite mettre mes compétences au service "
     "d'une entreprise en croissance comme la vôtre. Je serais ravie d'échanger lors d'un entretien.", None),
    ('Candidature Spontanée', 'tom.renaud@laposte.net',
     'Poste de commercial ?',
     "Bonjour, je ne sais pas si vous recrutez en ce moment mais je me permets de vous envoyer "
     "mon profil : 6 ans de vente B2B dans le logiciel. Disponible sous un mois.", None),
    ('Candidature Spontanée', 'ines.b@gmail.com',
     'Question sur vos tarifs… et sur vous',
     "Bonjour, je ne suis pas cliente : je suis designer UX et j'adore votre interface. "
     "Est-ce que vous recrutez ? Mon portfolio est en lien.",
     "« tarifs » dans l'objet, mais c'est une candidature"),
    ('Candidature Spontanée', 'hugo.petit@etu.univ-lyon.fr',
     'Envie de vous rejoindre',
     "Jeune diplômé en data science, je vous adresse ma candidature spontanée. Je suis mobile "
     "et disponible immédiatement pour un CDI.", None),

    # ── Demande de Congés & Absence ───────────────────────────────────────
    ('Demande de Congés & Absence', 'julie.fabre@notre-entreprise.fr',
     'Congés de Noël',
     "Salut Marc, je voudrais poser du 23 décembre au 2 janvier inclus. Mes dossiers seront à "
     "jour avant. Tu peux valider dans l'outil quand tu as un moment ?", None),
    ('Demande de Congés & Absence', 'r.meyer@notre-entreprise.fr',
     'Absence vendredi',
     "Bonjour, je serai absent vendredi pour un rendez-vous médical. Je rattraperai mes heures "
     "lundi. Merci !", None),
    ('Demande de Congés & Absence', 'n.cohen@notre-entreprise.fr',
     'RTT le 14',
     "Hello, est-ce que je peux prendre un RTT le 14 ? La démo client est le 15, tout sera prêt.", None),
    ('Demande de Congés & Absence', 'a.lopez@notre-entreprise.fr',
     'Arrêt maladie',
     "Bonjour, je vous transmets mon arrêt de travail jusqu'à mercredi. Désolée pour le "
     "désagrément, Paul a accès à mes dossiers en cours.", None),
    ('Demande de Congés & Absence', 'b.simon@notre-entreprise.fr',
     'Réunion de lundi',
     "Je ne pourrai pas être là lundi, j'ai posé un jour de congé il y a un mois. "
     "Est-ce qu'on peut valider mon congé parental à partir de février, on en parle à mon retour ?",
     "objet « réunion », contenu : absence + congé"),

    # ── Newsletter & Veille Sectorielle ───────────────────────────────────
    ('Newsletter & Veille Sectorielle', 'hebdo@lettre-du-numerique.fr',
     'La lettre du numérique #212',
     "Au sommaire cette semaine : les nouvelles règles de facturation électronique, trois "
     "outils d'IA testés pour les PME, et notre agenda des salons. Bonne lecture !", None),
    ('Newsletter & Veille Sectorielle', 'news@retail-insights.com',
     'Ce qui a changé dans le commerce ce mois-ci',
     "Chaque mois, nous résumons les tendances du commerce : panier moyen, livraison, "
     "paiement fractionné. Pour vous désinscrire, cliquez ici.", None),
    ('Newsletter & Veille Sectorielle', 'veille@observatoire-rh.org',
     'Veille RH – octobre',
     "Notre sélection d'articles du mois : télétravail, nouvelles obligations d'entretien "
     "professionnel, et une étude sur la rétention des talents.", None),
    ('Newsletter & Veille Sectorielle', 'digest@devtools-weekly.io',
     'Devtools Weekly: 10 liens à lire',
     "Les dix liens de la semaine pour les développeurs : un nouveau framework de tests, "
     "un retour d'expérience sur les migrations Postgres, et un outil de profilage.", None),
    ('Newsletter & Veille Sectorielle', 'infos@federation-pme.fr',
     'Alerte : nouvelle obligation au 1er janvier',
     "Dans ce numéro de notre lettre d'information : ce que change l'obligation de "
     "facturation électronique pour les petites entreprises, et comment s'y préparer.",
     "« Alerte » + « facturation » dans le texte, mais c'est une lettre d'information"),

    # ── Tentative de Fraude / Hameçonnage ─────────────────────────────────
    ('Tentative de Fraude / Hameçonnage', 'securite@micros0ft-support.com',
     'Votre compte sera suspendu',
     "Nous avons détecté une activité inhabituelle. Votre compte sera suspendu dans 24 h si vous "
     "ne confirmez pas votre mot de passe en cliquant sur le lien ci-dessous.", None),
    ('Tentative de Fraude / Hameçonnage', 'president.direction@gmail.com',
     'Virement confidentiel',
     "Bonjour, je suis en réunion et injoignable. J'ai besoin que tu effectues un virement de "
     "48 000 € aujourd'hui pour une acquisition confidentielle. N'en parle à personne, je t'envoie l'IBAN.", None),
    ('Tentative de Fraude / Hameçonnage', 'compta@hebergement-nordik-eu.net',
     'Changement de coordonnées bancaires',
     "Suite à un changement de banque, merci de régler désormais nos factures sur le nouvel "
     "IBAN ci-joint. L'ancien compte sera clôturé dès demain.",
     "ressemble à un fournisseur connu : c'est la fraude au changement d'IBAN"),
    ('Tentative de Fraude / Hameçonnage', 'colis@suivi-livraison-fr.info',
     'Votre colis est bloqué',
     "Votre colis n'a pas pu être livré. Des frais de réexpédition de 1,99 € sont nécessaires. "
     "Réglez-les ici avant ce soir pour éviter le retour à l'expéditeur.",
     "ressemble à un suivi de livraison"),
    ('Tentative de Fraude / Hameçonnage', 'factures@docu-sign-secure.co',
     'Facture impayée – document à signer',
     "Une facture impayée vous attend. Ouvrez le document et saisissez vos identifiants "
     "professionnels pour le consulter. Lien valable 2 heures.",
     "ressemble à une facture fournisseur"),

    # ── Invitation Réunion Calendrier ─────────────────────────────────────
    ('Invitation Réunion Calendrier', 'agenda@notre-entreprise.fr',
     'Invitation : Point projet – jeu. 10:00',
     "Vous êtes invité(e) à « Point projet refonte ». Jeudi 10:00–10:45, salle Everest et en visio. "
     "Accepter · Peut-être · Refuser", None),
    ('Invitation Réunion Calendrier', 'camille@client-agence.fr',
     'Un créneau la semaine prochaine ?',
     "Bonjour, pourrions-nous caler 30 minutes la semaine prochaine pour faire le point sur le "
     "déploiement ? Je suis dispo mardi après-midi ou jeudi matin.", None),
    ('Invitation Réunion Calendrier', 'rh@notre-entreprise.fr',
     'Réunion d’équipe mensuelle',
     "La réunion mensuelle aura lieu le 5 à 9h30 en salle du 3e étage. Ordre du jour : "
     "résultats du trimestre et organisation des congés d'hiver.",
     "parle de congés, mais c'est une invitation"),
    ('Invitation Réunion Calendrier', 'noreply@visio-meet.com',
     'Mis à jour : Revue de sprint',
     "L'événement « Revue de sprint » a été déplacé au vendredi 14:00–15:00. Lien de la visio "
     "inchangé.", None),
    ('Invitation Réunion Calendrier', 'thomas@partenaire-conseil.fr',
     'Déjeuner de travail',
     "Salut ! Ça te dit un déjeuner de travail le 18 pour parler du partenariat ? Je réserve "
     "si tu confirmes.", None),

    # ── Suivi de Livraison & Tracking ─────────────────────────────────────
    ('Suivi de Livraison & Tracking', 'suivi@transporteur-express.fr',
     'Votre colis est en cours de livraison',
     "Bonne nouvelle : votre colis 6A21984471 est en cours de livraison aujourd'hui entre "
     "13h et 17h. Suivez-le en temps réel dans votre espace.", None),
    ('Suivi de Livraison & Tracking', 'logistique@fournisseur-ecrans.com',
     'Expédition de votre commande 7731',
     "Votre commande de 15 écrans a quitté notre entrepôt. Numéro de suivi : TRK-7731-FR. "
     "Livraison estimée : mercredi.", None),
    ('Suivi de Livraison & Tracking', 'service.client@mobilier-pro.fr',
     'Livraison programmée',
     "Votre livraison de mobilier est programmée le 22 entre 8h et 12h. Merci de prévoir "
     "un accès pour un camion de 12 m³.", None),
    ('Suivi de Livraison & Tracking', 'notifications@point-relais.fr',
     'Votre colis vous attend',
     "Votre colis est disponible dans votre point relais pendant 10 jours. Présentez ce code "
     "de retrait : 448 219.", None),
    ('Suivi de Livraison & Tracking', 'expedition@imprimerie-delorme.fr',
     'Plaquettes : départ ce soir',
     "Vos 2 000 plaquettes partent ce soir par transporteur, numéro de suivi en pièce jointe. "
     "La facture suivra séparément.",
     "même fournisseur qu'une facture, mot « facture » présent"),
]

if __name__ == '__main__':
    jeu = []
    for i, (c, s, o, b, p) in enumerate(E, 1):
        assert c in CLASSES, c
        jeu.append({'id': f'm{i:02d}', 'attendu': c, 'expediteur': s,
                    'objet': o, 'corps': b, 'piege': p})
    par = {c: sum(1 for j in jeu if j['attendu'] == c) for c in CLASSES}
    assert all(v == 5 for v in par.values()), par
    json.dump({'classes': CLASSES, 'emails': jeu},
              open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'jeu_test.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(len(jeu), 'e-mails ·', sum(1 for j in jeu if j['piege']), 'pièges')
