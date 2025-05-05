import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# Charger les variables d'environnement
load_dotenv()

# Importation des modules personnalisés (dans le même dossier que bot.py)
from scrape_jobs import setup_scrape_command
from extract_cv import setup_cv_command
from match_cv_offer import setup_compare_command
from generate_cover_letter import setup_letter_command
from utils.helper import UserData, user_data

# Importation des modules des groupes 4 et 5
import codegr4
import codegr5

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialisation des variables pour les API keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialisation du module du groupe 5 si la clé Gemini est disponible
groupe5_module = None
if GEMINI_API_KEY:
    groupe5_module = codegr5.integrer_module_groupe5(GEMINI_API_KEY)

@bot.event
async def on_ready():
    print(f'✅ Bot connecté en tant que {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ Commandes synchronisées: {len(synced)}")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes: {e}")

# Configuration des commandes du groupe 4 (analyse de CV)
def setup_groupe4_command(bot):
    @bot.tree.command(name="analyser_cv", description="Analyse un CV au format PDF et extrait ses informations")
    async def analyser_cv(interaction: discord.Interaction, cv_pdf: discord.Attachment):
        await interaction.response.defer(thinking=True)
        
        if not cv_pdf.filename.lower().endswith('.pdf'):
            await interaction.followup.send("❌ Veuillez télécharger un fichier PDF valide.")
            return
            
        try:
            # Télécharger le fichier PDF
            pdf_bytes = await cv_pdf.read()
            
            # Choisir le modèle LLM à utiliser
            llm_provider = codegr4.LLMProvider.GEMINI if GEMINI_API_KEY else codegr4.LLMProvider.MISTRAL
            
            # Traiter le CV
            success, result = codegr4.process_cv_file(
                pdf_bytes,
                llm_provider=llm_provider,
                mistral_api_key=MISTRAL_API_KEY,
                gemini_api_key=GEMINI_API_KEY
            )
            
            if success:
                # Stocker les données du CV pour l'utilisateur
                user_id = str(interaction.user.id)
                if user_id not in user_data:
                    user_data[user_id] = UserData()
                user_data[user_id].cv_data = result
                
                # Envoyer un résumé des informations extraites
                cv_summary = (
                    f"✅ CV analysé avec succès pour {result['prenom_nom']} !\n\n"
                    f"📧 Email: {result['email']}\n"
                    f"📞 Téléphone: {result['telephone']}\n"
                    f"💼 Formation: {len(result['formation'])} diplôme(s)\n"
                    f"🏢 Expérience: {len(result['experience'])} poste(s)\n"
                    f"🛠️ Compétences techniques: {len(result['competences_techniques'])}\n"
                    f"🧠 Soft skills: {len(result['soft_skills'])}\n"
                    f"🗣️ Langues: {len(result['langues'])}\n"
                    f"🏆 Certifications: {len(result['certifications'])}\n\n"
                    f"Les données du CV ont été enregistrées et peuvent maintenant être utilisées pour comparer avec des offres d'emploi."
                )
                
                await interaction.followup.send(cv_summary)
                
                # Sauvegarder le résultat dans un fichier pour référence
                output_path = codegr4.save_cv_result_to_file(result, cv_pdf.filename, output_dir="resultats_cv")
                if output_path:
                    with open(output_path, "r", encoding="utf-8") as f:
                        await interaction.followup.send(
                            "📄 Voici le résultat détaillé de l'analyse:",
                            file=discord.File(output_path)
                        )
            else:
                await interaction.followup.send(f"❌ Erreur: {result}")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Une erreur est survenue lors de l'analyse du CV: {str(e)}")

# Configuration des commandes du groupe 5 (génération de lettre de motivation)
def setup_groupe5_command(bot):
    @bot.tree.command(name="generer_lettre", description="Génère une lettre de motivation basée sur votre CV et une offre d'emploi")
    async def generer_lettre(
        interaction: discord.Interaction,
        motivation: str = None,
        lien_entreprise: str = None,
        contraintes: str = None
    ):
        await interaction.response.defer(thinking=True)
        
        # Vérifier si le module du groupe 5 est initialisé
        if not groupe5_module:
            await interaction.followup.send("❌ La génération de lettres n'est pas disponible. Clé API Gemini manquante.")
            return
        
        # Récupérer les données de l'utilisateur
        user_id = str(interaction.user.id)
        if user_id not in user_data or not user_data[user_id].cv_data:
            await interaction.followup.send("❌ Vous devez d'abord analyser votre CV avec `/analyser_cv`.")
            return
            
        if not user_data[user_id].selected_job:
            await interaction.followup.send("❌ Vous devez d'abord sélectionner une offre d'emploi avec `/scrape` puis `/compare`.")
            return
        
        # Récupérer les données du CV et de l'offre
        cv_data = user_data[user_id].cv_data
        job_data = user_data[user_id].selected_job
        
        # Préparer les informations personnelles supplémentaires pour la lettre
        infos_perso = {
            "motivation": motivation or "",
            "lien_entreprise": lien_entreprise or "",
            "contraintes": contraintes or ""
        }
        
        try:
            # Générer la lettre de motivation
            success, chemin_fichier, contenu_lettre = groupe5_module.generer_lettre_motivation(
                cv_data, job_data, infos_perso
            )
            
            if success:
                # Envoyer un aperçu du contenu de la lettre
                preview = contenu_lettre[:1500] + ("..." if len(contenu_lettre) > 1500 else "")
                
                await interaction.followup.send(
                    f"✅ Lettre de motivation générée avec succès pour le poste de **{job_data['titre']}** chez **{job_data['entreprise']}** !\n\n"
                    f"**Aperçu :**\n```\n{preview}\n```"
                )
                
                # Envoyer le fichier Word de la lettre
                with open(chemin_fichier, "rb") as f:
                    await interaction.followup.send(
                        "📄 Voici votre lettre de motivation au format Word :",
                        file=discord.File(chemin_fichier)
                    )
            else:
                await interaction.followup.send(
                    "❌ Votre CV n'est pas suffisamment pertinent pour cette offre (moins de 70% de compatibilité).\n"
                    "Essayez avec une autre offre ou améliorez votre CV pour mieux correspondre aux exigences."
                )
                
        except Exception as e:
            await interaction.followup.send(f"❌ Une erreur est survenue lors de la génération de la lettre: {str(e)}")

# Configuration des commandes
def setup(bot):
    setup_scrape_command(bot)
    setup_cv_command(bot)
    setup_compare_command(bot)
    setup_letter_command(bot)
    setup_groupe4_command(bot)
    setup_groupe5_command(bot)

# Initialiser les commandes
setup(bot)

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    print("❌ Le token Discord est introuvable. Vérifie ton fichier .env.")
else:
    print(f"Démarrage du bot avec le token: {'*' * len(TOKEN)}")  # Masque le token pour plus de sécurité
    bot.run(TOKEN)