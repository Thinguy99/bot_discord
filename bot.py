import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# Charger les variables d'environnement
load_dotenv()

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Importation des modules personnalisés
from commands.scrape_jobs import setup_scrape_command
from commands.extract_cv import setup_cv_command
from commands.match_cv_offer import setup_compare_command
from commands.generate_cover_letter import setup_letter_command
from commands.scrape_internship import setup_internship_command
from utils.helper import UserData, user_data

# On ready event
@bot.event
async def on_ready():
    print(f'✅ Bot connecté en tant que {bot.user}')
    
    # Setup each command with specific error handling
    command_setups = [
        ("scrape_jobs", setup_scrape_command),
        ("extract_cv", setup_cv_command),
        ("match_cv_offer", setup_compare_command),
        ("generate_cover_letter", setup_letter_command),
        ("scrape_internship", setup_internship_command)
    ]
    
    for name, setup_func in command_setups:
        try:
            if asyncio.iscoroutinefunction(setup_func):
                await setup_func(bot)
            else:
                print(f"⚠️ {name} n'est pas une fonction asynchrone, conversion...")
                # Call non-async setup functions directly
                setup_func(bot)
        except Exception as e:
            print(f"❌ Erreur lors de la configuration de {name}: {e}")
    
    # Synchronize commands AFTER all setup
    try:
        synced = await bot.tree.sync()
        print(f"✅ Commandes synchronisées: {len(synced)}")
        print(f"✅ Commandes disponibles: {[cmd.name for cmd in bot.tree.get_commands()]}")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes: {e}")

# Start the bot
token = os.getenv('DISCORD_TOKEN')
print(f"Démarrage du bot avec le token: {'*' * len(token)}")
bot.run(token)