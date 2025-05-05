import os
import io
import json
import tempfile
import requests
import PyPDF2
import re
import google.generativeai as genai
from enum import Enum
from pathlib import Path

class LLMProvider(Enum):
    MISTRAL = "mistral"
    GEMINI = "gemini"

def parse_cv(pdf_content, llm_provider=LLMProvider.MISTRAL, mistral_api_key=None, gemini_api_key=None):
    """
    Analyse un CV au format PDF et extrait les informations structurées au format JSON.
    
    Args:
        pdf_content (bytes): Contenu binaire du fichier PDF du CV
        llm_provider (LLMProvider): Fournisseur LLM à utiliser (MISTRAL ou GEMINI)
        mistral_api_key (str, optional): Clé API pour Mistral AI
        gemini_api_key (str, optional): Clé API pour Google Gemini
    
    Returns:
        dict: Données structurées du CV au format Python dict
        None: En cas d'erreur
    """
    try:
        # Vérifier les clés API requises
        if llm_provider == LLMProvider.MISTRAL and not mistral_api_key:
            raise ValueError("Clé API Mistral requise pour utiliser Mistral AI")
        if llm_provider == LLMProvider.GEMINI and not gemini_api_key:
            raise ValueError("Clé API Gemini requise pour utiliser Google Gemini")
        
        # 1. Extraire le texte du PDF
        texte_cv = extraire_texte_pdf(pdf_content)
        if not texte_cv:
            raise ValueError("Impossible d'extraire le texte du PDF")
        
        # 2. Générer le JSON avec le LLM choisi
        if llm_provider == LLMProvider.MISTRAL:
            json_str = generer_json_mistral(texte_cv, mistral_api_key)
        else:  # GEMINI
            json_str = generer_json_gemini(texte_cv, gemini_api_key)
        
        if not json_str:
            raise ValueError(f"Erreur lors de la génération du JSON avec {llm_provider.value}")
        
        # 3. Convertir la chaîne JSON en dictionnaire Python
        return json.loads(json_str)
    
    except Exception as e:
        print(f"Erreur lors de l'analyse du CV: {str(e)}")
        return None

def extraire_texte_pdf(fichier_pdf):
    """
    Extrait le texte d'un fichier PDF
    
    Args:
        fichier_pdf (bytes): Contenu binaire du fichier PDF
        
    Returns:
        str: Texte extrait du PDF ou None en cas d'erreur
    """
    try:
        texte = ""
        # Utiliser BytesIO pour lire les données binaires
        pdf_stream = io.BytesIO(fichier_pdf)
        lecteur_pdf = PyPDF2.PdfReader(pdf_stream)
        for page in lecteur_pdf.pages:
            texte += page.extract_text() + "\n"
        return texte
    except Exception as e:
        print(f"Erreur lors de l'extraction du texte du PDF: {e}")
        return None

def generer_json_mistral(texte_cv, api_key):
    """
    Utilise l'API Mistral pour générer le JSON structuré à partir du texte du CV
    
    Args:
        texte_cv (str): Texte du CV extrait du PDF
        api_key (str): Clé API Mistral
        
    Returns:
        str: JSON généré par Mistral ou None en cas d'erreur
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    API_URL = "https://api.mistral.ai/v1/chat/completions"
    
    # Liste des compétences techniques et soft skills pour aider le modèle
    liste_competences = """
    Exemples de compétences techniques à identifier (UNIQUEMENT les outils concrets et langages de programmation):
    
    # Langages de programmation
    Python, R, Java, C, C++, C#, JavaScript, TypeScript, PHP, Ruby, Swift, Kotlin, Go, Rust, SQL, Scala, Perl, Shell, Bash, PowerShell, MATLAB, VBA
    
    # Data Science et ML (outils uniquement)
    TensorFlow, PyTorch, Keras, Scikit-learn, Pandas, NumPy, SciPy, NLTK, spaCy, Matplotlib, Seaborn
    
    # Web et Frontend
    HTML, CSS, Bootstrap, React, Angular, Vue.js, jQuery, REST API, GraphQL, Node.js, Express
    
    # Bases de données
    MySQL, PostgreSQL, SQLite, Oracle, MongoDB, Redis, Elasticsearch, NoSQL, SQL Server, MariaDB
    
    # DevOps et Cloud
    AWS, Azure, GCP, Docker, Kubernetes, Git, GitHub, GitLab, CI/CD, Jenkins, Linux, Unix, Windows, MacOS
    
    # Bureautique et outils
    Microsoft Office, Microsoft 365, Office 365, Suite Office, Excel, Word, PowerPoint, Access, Outlook, OneNote, SharePoint, OneDrive, Teams, Microsoft Teams, Tableau, Power BI, SAP, Salesforce, Jira, Confluence, Trello, MS Project
    
    # Autres outils techniques
    LaTeX, RStudio, Jupyter, Orange, SAS, SPSS
    
    ATTENTION: N'inclus PAS les domaines de connaissances ou sujets théoriques comme compétences techniques.
    Par exemple, n'inclus PAS: Économie, Microéconomie, Macroéconomie, Comptabilité, Finance, Droit, Mathématiques, 
    Statistiques théoriques, Machine Learning théorique, etc. 
    
    Inclus UNIQUEMENT les outils et langages concrets que la personne sait utiliser.
    
    Exemples de soft skills à identifier:
    Communication, leadership, travail d'équipe, résolution de problèmes, gestion de projet, organisation, autonomie, adaptabilité, créativité, esprit critique, négociation, intelligence émotionnelle, gestion du temps, gestion du stress, écoute active, empathie, flexibilité, prise de décision, persuasion, présentation, prise de parole en public
    
    Exemples de certifications:
    Permis B, Permis BVA, TOEIC, TOEFL, IELTS, Cambridge Certificate, DELF, DALF, HSK, PIX, Google Analytics, Certification Microsoft, Certification AWS, Certification Azure, ITIL, PMP, PRINCE2
    """
    
    # Construire le prompt pour Mistral
    prompt = f"""
    Voici le texte complet d'un CV extrait d'un fichier PDF. Analyse-le et convertis-le directement en JSON avec la structure suivante:

    ```json
    {{
      "prenom_nom": "string",
      "email": "string",
      "telephone": "string",
      "linkedin": "string (seulement le nom d'utilisateur, pas l'URL complète, ou vide si non présent)",
      "github": "string (seulement le nom d'utilisateur, pas l'URL complète, ou vide si non présent)",
      "competences_techniques": [
        "compétence technique 1",
        "compétence technique 2"
      ],
      "soft_skills": [
        "soft skill 1",
        "soft skill 2"
      ],
      "langues": [
        "string (langue et niveau)"
      ],
      "certifications": [
        "string (certification 1)",
        "string (certification 2)"
      ],
      "formation": [
        {{
          "titre": "string (diplôme et spécialité)",
          "etablissement": "string (nom de l'école/université)",
          "periode": "string (dates de début et fin)",
          "details": [
            "string (enseignements, mentions, etc.)"
          ]
        }}
      ],
      "experience": [
        {{
          "titre": "string (intitulé du poste)",
          "entreprise": "string (nom de l'entreprise)",
          "lieu": "string (ville/pays ou télétravail)",
          "periode": "string (dates de début et fin)",
          "details": [
            "string (responsabilités, accomplissements)"
          ]
        }}
      ]
    }}
    ```

    Instructions spéciales:
    - Inclus TOUJOURS les champs "linkedin" et "github" dans le JSON, même s'ils sont vides ("").
    - Pour LinkedIn, si tu trouves une URL comme "linkedin.com/in/nom-utilisateur", n'inclus que "nom-utilisateur". Si tu trouves directement "/linkedin-innom-utilisateur", n'inclus que "nom-utilisateur".
    - Pour GitHub, si tu trouves une URL comme "github.com/nom-utilisateur", n'inclus que "nom-utilisateur". Si tu trouves directement "/githubnom-utilisateur", n'inclus que "nom-utilisateur".
    - Si aucun profil LinkedIn ou GitHub n'est mentionné dans le CV, laisse ces champs vides: "linkedin": "", "github": "".
    
    - IMPORTANT: Pour les compétences techniques, inclus UNIQUEMENT les langages de programmation, logiciels, et outils concrets.
      * Ne pas inclure dans cette section les domaines de connaissances théoriques comme l'économie, la finance, les mathématiques, etc.
      * Limite-toi aux compétences techniques concrètes et opérationnelles (langages, logiciels, frameworks, etc.)
      * Assure-toi d'inclure les outils de la suite Microsoft Office (Word, Excel, PowerPoint) et Microsoft 365 s'ils sont mentionnés dans le CV
    
    - Identifie et liste toutes les soft skills (compétences personnelles, interpersonnelles et transversales).
    
    - CERTIFICATIONS:
      * Recherche et inclus toutes les certifications mentionnées dans le CV.
      * Permis de conduire (B, BVA, etc.), certifications de langue (TOEIC, TOEFL, etc.), certifications informatiques (PIX, etc.)
      * Si aucune certification n'est mentionnée, laisse la liste vide: []
    
    - Tu dois ABSOLUMENT inclure les champs "competences_techniques", "soft_skills" et "certifications" dans le JSON final, même s'ils sont vides.

    {liste_competences}

    Texte du CV:
    {texte_cv}

    Retourne UNIQUEMENT le JSON sans aucun autre commentaire. Assure-toi que le format est valide.
    """
    
    # Préparer la requête pour l'API
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2  # Température plus basse pour respecter plus strictement le format
    }
    
    try:
        # Envoyer la requête à l'API Mistral
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        # Extraire la réponse
        resultat = response.json()
        reponse_mistral = resultat["choices"][0]["message"]["content"]
        
        # Extraire uniquement le JSON de la réponse (au cas où Mistral ajoute des commentaires)
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*(\{[\s\S]*\})\s*$"
        match = re.search(json_pattern, reponse_mistral)
        
        if match:
            json_str = match.group(1) or match.group(2)
            
            # Vérifier que le JSON est valide
            try:
                json_obj = json.loads(json_str)
                
                # Post-traitement pour détecter Microsoft Office et ses composants
                if "competences_techniques" in json_obj:
                    # Liste des termes bureautiques à rechercher dans le texte du CV
                    bureautique_terms = [
                        "Microsoft Office", "MS Office", "Office", "Suite Office", 
                        "Microsoft 365", "Office 365", "M365", "O365",
                        "Excel", "Word", "PowerPoint", "PPT", "Access", "Outlook",
                        "OneNote", "SharePoint", "OneDrive", "Teams", "Microsoft Teams"
                    ]
                    
                    # Vérifier si ces termes sont dans le texte du CV mais pas dans les compétences
                    found_terms = set()
                    for term in bureautique_terms:
                        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                        if pattern.search(texte_cv):
                            # Normaliser le nom de la compétence (première lettre de chaque mot en majuscule)
                            normalized_term = ' '.join(word.capitalize() for word in term.split())
                            found_terms.add(normalized_term)
                    
                    # Ajouter les termes trouvés qui ne sont pas déjà dans les compétences
                    for term in found_terms:
                        if not any(comp.lower() == term.lower() for comp in json_obj["competences_techniques"]):
                            json_obj["competences_techniques"].append(term)
                
                # Vérifier que tous les champs requis sont présents, sinon les ajouter
                champs_requis = ["linkedin", "github", "competences_techniques", "soft_skills", "certifications"]
                for champ in champs_requis:
                    if champ not in json_obj:
                        if champ in ["linkedin", "github"]:
                            json_obj[champ] = ""
                        elif champ in ["competences_techniques", "soft_skills", "certifications"]:
                            json_obj[champ] = []
                
                return json.dumps(json_obj, ensure_ascii=False, indent=2)
            except json.JSONDecodeError as e:
                print(f"Erreur lors du décodage du JSON: {e}")
                return None
        else:
            # Si Mistral n'a pas utilisé de balises de code, essayons de parser directement
            try:
                json_obj = json.loads(reponse_mistral)
                # Post-traitement identique à celui ci-dessus...
                # Ajout des compétences bureautiques et vérification des champs requis
                return json.dumps(json_obj, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                print("Impossible d'extraire un JSON valide de la réponse Mistral")
                return None
    
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la communication avec l'API Mistral: {e}")
        return None

def generer_json_gemini(texte_cv, api_key):
    """
    Utilise l'API Google Gemini pour générer le JSON structuré à partir du texte du CV
    
    Args:
        texte_cv (str): Texte du CV extrait du PDF
        api_key (str): Clé API Google Gemini
        
    Returns:
        str: JSON généré par Gemini ou None en cas d'erreur
    """
    try:
        # Configurer l'API Gemini
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest")
        
        # Construire le prompt pour Gemini
        prompt = f"""
        Voici le texte complet d'un CV extrait d'un fichier PDF. Analyse-le et convertis-le directement en JSON avec la structure suivante:

        ```json
        {{
          "prenom_nom": "string",
          "email": "string",
          "telephone": "string",
          "linkedin": "string (seulement le nom d'utilisateur, pas l'URL complète, ou vide si non présent)",
          "github": "string (seulement le nom d'utilisateur, pas l'URL complète, ou vide si non présent)",
          "competences_techniques": [
            "compétence technique 1",
            "compétence technique 2"
          ],
          "soft_skills": [
            "soft skill 1",
            "soft skill 2"
          ],
          "langues": [
            "string (langue et niveau)"
          ],
          "certifications": [
            "string (certification 1)",
            "string (certification 2)"
          ],
          "formation": [
            {{
              "titre": "string (diplôme et spécialité)",
              "etablissement": "string (nom de l'école/université)",
              "periode": "string (dates de début et fin)",
              "details": [
                "string (enseignements, mentions, etc.)"
              ]
            }}
          ],
          "experience": [
            {{
              "titre": "string (intitulé du poste)",
              "entreprise": "string (nom de l'entreprise)",
              "lieu": "string (ville/pays ou télétravail)",
              "periode": "string (dates de début et fin)",
              "details": [
                "string (responsabilités, accomplissements)"
              ]
            }}
          ]
        }}
        ```

        Instructions spéciales:
        - Inclus TOUJOURS les champs "linkedin" et "github" dans le JSON, même s'ils sont vides ("").
        - Pour LinkedIn, si tu trouves une URL comme "linkedin.com/in/nom-utilisateur", n'inclus que "nom-utilisateur". Si tu trouves directement "/linkedin-innom-utilisateur", n'inclus que "nom-utilisateur".
        - Pour GitHub, si tu trouves une URL comme "github.com/nom-utilisateur", n'inclus que "nom-utilisateur". Si tu trouves directement "/githubnom-utilisateur", n'inclus que "nom-utilisateur".
        - Si aucun profil LinkedIn ou GitHub n'est mentionné dans le CV, laisse ces champs vides: "linkedin": "", "github": "".

        - IMPORTANT: Pour les compétences techniques, inclus UNIQUEMENT les langages de programmation, logiciels, et outils concrets.
          * Ne pas inclure dans cette section les domaines de connaissances théoriques comme l'économie, la finance, les mathématiques, etc.
          * Limite-toi aux compétences techniques concrètes et opérationnelles (langages, logiciels, frameworks, etc.)

        - Identifie et liste toutes les soft skills (compétences personnelles, interpersonnelles et transversales).

        - CERTIFICATIONS:
          * Recherche et inclus toutes les certifications mentionnées dans le CV.
          * Permis de conduire (B, BVA, etc.), certifications de langue (TOEIC, TOEFL, etc.), certifications informatiques (PIX, etc.)
          * Si aucune certification n'est mentionnée, laisse la liste vide: []

        - Tu dois ABSOLUMENT inclure les champs "competences_techniques", "soft_skills" et "certifications" dans le JSON final, même s'ils sont vides.

        Texte du CV:
        {texte_cv}

        Retourne UNIQUEMENT le JSON sans aucun autre commentaire. Assure-toi que le format est valide.
        """
        
        # Envoyer la requête à l'API Gemini
        response = gemini_model.generate_content(prompt)
        
        # Récupérer la réponse de Gemini
        result_json = response.text
        
        # Nettoyer et vérifier le JSON
        json_pattern = r"```json\s*([\s\S]*?)\s*```|^\s*(\{[\s\S]*\})\s*$"
        match = re.search(json_pattern, result_json)
        
        if match:
            json_str = match.group(1) or match.group(2)
            # Vérifier que le JSON est valide
            try:
                json_obj = json.loads(json_str)
                # Vérifier les champs requis
                champs_requis = ["linkedin", "github", "competences_techniques", "soft_skills", "certifications"]
                for champ in champs_requis:
                    if champ not in json_obj:
                        if champ in ["linkedin", "github"]:
                            json_obj[champ] = ""
                        elif champ in ["competences_techniques", "soft_skills", "certifications"]:
                            json_obj[champ] = []
                            
                return json.dumps(json_obj, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                print("Erreur lors du décodage du JSON retourné par Gemini")
                return None
        else:
            try:
                # Essayer de parser directement si pas de balises
                json_obj = json.loads(result_json)
                # Vérifier les champs requis
                champs_requis = ["linkedin", "github", "competences_techniques", "soft_skills", "certifications"]
                for champ in champs_requis:
                    if champ not in json_obj:
                        if champ in ["linkedin", "github"]:
                            json_obj[champ] = ""
                        elif champ in ["competences_techniques", "soft_skills", "certifications"]:
                            json_obj[champ] = []
                            
                return json.dumps(json_obj, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                print("Impossible d'extraire un JSON valide de la réponse Gemini")
                return None
    
    except Exception as e:
        print(f"Erreur lors de l'utilisation de l'API Gemini: {e}")
        return None

# Fonction pour utilisation depuis Discord
def process_cv_file(file_content, llm_provider=LLMProvider.MISTRAL, mistral_api_key=None, gemini_api_key=None):
    """
    Traite un fichier PDF de CV et retourne un dictionnaire JSON structuré
    
    Args:
        file_content (bytes): Contenu binaire du fichier PDF
        llm_provider (LLMProvider): Fournisseur LLM (MISTRAL ou GEMINI)
        mistral_api_key (str): Clé API Mistral
        gemini_api_key (str): Clé API Gemini
        
    Returns:
        tuple: (success, result)
            - success (bool): True si le traitement a réussi, False sinon
            - result (dict/str): Données du CV au format dict si success=True, 
                               message d'erreur si success=False
    """
    try:
        # Analyser le CV
        cv_data = parse_cv(
            file_content, 
            llm_provider=llm_provider,
            mistral_api_key=mistral_api_key,
            gemini_api_key=gemini_api_key
        )
        
        if cv_data:
            return True, cv_data
        else:
            return False, "Erreur lors de l'analyse du CV"
    
    except Exception as e:
        return False, f"Erreur lors du traitement du fichier: {str(e)}"

# Fonction pour sauvegarder le résultat dans un fichier
def save_cv_result_to_file(cv_data, original_filename, output_dir=None):
    """
    Sauvegarde les données du CV dans un fichier JSON
    
    Args:
        cv_data (dict): Données structurées du CV
        original_filename (str): Nom du fichier PDF original
        output_dir (str, optional): Répertoire de sortie
        
    Returns:
        str: Chemin du fichier JSON créé ou None en cas d'erreur
    """
    try:
        # Créer le nom du fichier de sortie
        base_filename = os.path.splitext(os.path.basename(original_filename))[0]
        output_filename = f"{base_filename}_resultat.json"
        
        # Définir le chemin du fichier
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
        else:
            output_path = output_filename
        
        # Écrire le fichier JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cv_data, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier JSON: {e}")
        return None