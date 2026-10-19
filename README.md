# Fab Discovery Loop

[English](README.en.md) · [Español](README.es.md)

**Quel essai de fabrication mérite vraiment d’être fait ensuite ?**

Un laboratoire local choisit l’expérience qui distingue le mieux des hypothèses explicites sur un procédé, par unité de coût. Après une observation, il met à jour leurs probabilités et recalcule le prochain essai. Les limites machine, capacités manquantes, expériences en attente, budget et risque conditionnel restent visibles.

![Démonstration synthétique : choix de la prochaine expérience](docs/preview-fr.png)

## Essayer

Python 3.11 ou supérieur, bibliothèque standard uniquement. Aucune clé, aucun matériel connecté.

```sh
python3 -m fab_discovery serve --lang fr
```

Ouvrir `http://127.0.0.1:8765/?lang=fr`. Choisir l’hypothèse vraie du **simulateur synthétique**, simuler un essai, regarder les croyances évoluer, puis exporter hypothèses et observations. Le volet de saisie permet d’enregistrer une observation fournie ; ce geste ne prouve pas sa provenance instrumentale.

```sh
python3 -m fab_discovery demo --lang fr
python3 -m fab_discovery analyze fab_discovery/examples/process-window.json
python3 -m fab_discovery observe dossier.json p1-d5 underfused mesure-001 > suite.json
python3 -m fab_discovery benchmark > benchmark.json
```

L’installation `pip install .` fournit aussi `fab-discovery`. L’interface et les messages CLI sont disponibles en FR/EN/ES.

## Une boucle d’apprentissage vérifiable

1. Décrire des hypothèses finies : seuil de formation, seuil de dommage, largeur des transitions et poids initial.
2. Fournir les expériences candidates : puissance, durée, coût, capacités nécessaires.
3. Calculer exactement la réduction **attendue** d’entropie, en intégrant les trois résultats possibles : `underfused`, `good`, `damaged`.
4. Écarter les expériences hors budget, hors capacité, en attente ou au-dessus du risque conditionnel fourni ; classer le reste par information attendue/coût.
5. Enregistrer le résultat et mettre à jour les poids bayésiens en espace logarithmique.

Un même `evidence_id` rejoué avec le même résultat ne consomme pas deux fois le budget et n’est pas compté deux fois. Un contenu différent sous cet identifiant est rejeté. Sans identifiant, chaque observation est considérée comme une répétition indépendante. Une observation réellement effectuée peut être enregistrée même si elle aurait été exclue de la recommandation : on conserve aussi les échecs.

La recommandation n’exécute ni ne réserve une machine. Le coût est déduit lors de l’enregistrement d’une observation ; une équipe doit gérer séparément commandes, réservations et engagements financiers. L’empreinte du dossier lie chaque recommandation aux hypothèses et mesures fournies.

## Comparaison reproductible, avec compromis

`benchmark` compare trois stratégies myopes sur les trois hypothèses vraies possibles, 20 graines et au plus huit essais par campagne. Budget initial : 24 unités. Les tirages aléatoires sont partagés par graine, expérience et numéro de répétition.

| Stratégie            | Coût moyen | Entropie finale moyenne, bits | Poids final moyen de l’hypothèse vraie | Essais endommagés moyens |
| -------------------- | ---------: | ----------------------------: | -------------------------------------: | -----------------------: |
| Information/coût     |      23,14 |                         0,095 |                                  0,973 |                    0,567 |
| Rendement prévu/coût |      23,37 |                         0,203 |                                  0,930 |                    0,417 |
| Moins cher           |      16,00 |                         1,414 |                                  0,399 |                    0,000 |

Ici, apprendre davantage s’accompagne de plus de dommages simulés ; le moins cher consomme moins de budget. Le poids de l’hypothèse vraie **n’est pas un taux de précision industriel**. Les résultats dépendent de ces modèles jouets, de leurs paramètres et de ces graines. Aucun avantage sur BayBE ou sur un procédé réel n’a été mesuré.

## Comparaison avec l’existant et limites

[BayBE](https://github.com/emdgroup/baybe) propose déjà l’optimisation bayésienne et le plan d’expériences généralistes. Ce dépôt ne réinvente pas ces méthodes : il fournit une petite boucle autonome centrée sur la distinction d’hypothèses, les exclusions explicites et une démo lisible sans dépendances.

[Atomic Machines](https://www.atomicmachines.com/matter-compiler) décrit une fabrication qui conçoit, produit et mesure. L’inspiration porte sur ce cycle ; **aucune API, machine, licence ou relation Atomic Machines n’est intégrée**. Par rapport à [MeasurePlan](https://github.com/gbesse/measureplan), qui alloue des contrôles, cette boucle change le prochain essai à partir de l’information apprise.

Le modèle est volontairement simplifié : deux seuils de dose et trois résultats catégoriels. Les observations sont supposées conditionnellement indépendantes. Un modèle absent ne sera jamais découvert ; un posterior très confiant peut donc être faux. Le risque prédit n’est ni un certificat de sécurité, ni une validation physique. Pas d’optimisation de lots parallèles, de modèle continu ou de connecteur industriel. Les données du simulateur sont synthétiques et marquées dans le journal.

## Validation

```sh
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:browser
npm run format:check
```

Quatorze tests contrôlent notamment le calcul d’information face à une formulation KL indépendante, les exclusions, les répétitions, le budget et la stabilité numérique. Les parcours navigateur vérifient FR/EN/ES, simulation, observation saisie, risque, export et mobile. La CI vérifie Python 3.11/3.12 et l’installation de la roue hors des sources. Licence MIT ; alpha de recherche.
