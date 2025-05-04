## Groupe 5 – Utilisation des LLMs pour l’analyse de CV et la génération de lettres de motivation 

## Objectif : Ce projet explore l’utilisation de Large Language Models (LLMs)  – Gemini – pour : 
* Comparer un CV avec une fiche de poste afin de vérifier la pertinence de la candidature.
* Générer automatiquement une lettre de motivation personnalisée en s’appuyant sur le CV, la fiche de poste et d’éventuelles informations complémentaires fournies par l’utilisateur.
  L’objectif est de proposer un bot capable de livrer un retour rapide et personnalisé.

## 📁 Étapes de fonctionnement :
   1. Analyse de pertinence : Le CV et la fiche de poste sont nettoyés, puis un prompt ultra‑court demande à Gemini « oui/non » : “oui” si ≥ 70 % des exigences sont couvertes, sinon arrêt ou suggestion d’amélioration.
   2. Rédaction de la lettre : Si la réponse est positive, un prompt détaillé demande au LLM de rédiger une lettre d’environ 350 mots, professionnelle et personnalisée et un script qui contrôle la longueur et l'orthographe.
   3. Enrichir le prompt : On interroge brièvement le candidat (disponibilités, priorités, réalisations clés) pour enrichir le prompt, ce qui renforce la pertinence et la personnalisation de la lettre générée.
   4. Production du .docx : La lettre validée est déposée dans un Word à l’aide de `python‑docx` (Calibri 11 pt, marges A4, en‑tête avec coordonnées), puis enregistrée localement sous **Lettre_{Nom}_{Date}.docx**.

## ⚙️ Prérequis :
Python ≥ 3.10 
Clé API Google Gemini 

## Auteurs :

Aymane AIBICHI 
Zineb MANAR
Ali BOUGUERRA
Nawel ARIF
Nhung Nguyen
