import csv
import json
import logging
import os
import io
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from jobspy import scrape_jobs
import pandas as pd
import re
import asyncio
from typing import Optional

# Configuration du logging
def configure_logging():
    """Set up basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler('job_scraper.log'), logging.StreamHandler()]
    )

def scrape_job_listings(search_params):
    """Scrape job listings based on provided parameters"""
    try:
        logging.info(f"Starting job scraping with parameters: {search_params}")
        jobs = scrape_jobs(
            site_name=search_params['site_names'],
            search_term=search_params['search_term'],
            location=search_params['location'],
            results_wanted=search_params['results_wanted'],
            hours_old=search_params['hours_old'],
            country_indeed=search_params['country_indeed']
        )
        logging.info(f"Successfully scraped {len(jobs)} jobs")
        return jobs
    except Exception as e:
        logging.error(f"Error during job scraping: {str(e)}")
        raise

def clean_text_field(text):
    """Basic text cleaning for all string fields"""
    if not isinstance(text, str) or pd.isna(text):
        return ""
    # Remove extra spaces
    return re.sub(r'\s+', ' ', ''.join(c for c in ' '.join(text.splitlines()) if c.isprintable())).strip()

def clean_job_data(jobs_df):
    """Clean and preprocess the scraped job data"""
    try:
        df = jobs_df.copy()
        
        # Remove duplicates
        initial_count = len(df)
        df.drop_duplicates(subset=['job_url'], keep='first', inplace=True)
        logging.info(f"Removed {initial_count - len(df)} duplicate jobs")
        
        # Select and clean columns
        columns_to_keep = ['job_id', 'title', 'company', 'location', 'job_type', 
                          'date_posted', 'job_url', 'description', 'salary', 'job_site']
        columns_to_keep = [col for col in columns_to_keep if col in df.columns]
        df = df[columns_to_keep]
        
        # Clean text 
        for col in ['title', 'company', 'location', 'description', 'salary']:
            if col in df.columns:
                df[col] = df[col].apply(clean_text_field)
        
        # Convert dates
        if 'date_posted' in df.columns:
            df['date_posted'] = pd.to_datetime(df['date_posted'], errors='coerce')
        
        # Job types
        if 'job_type' in df.columns:
            job_type_map = {
                'full': 'Full-time', 'temps plein': 'Full-time', 'cdi': 'Full-time',
                'part': 'Part-time', 'temps partiel': 'Part-time',
                'contract': 'Contract', 'cdd': 'Contract',
                'intern': 'Internship', 'stage': 'Internship',
                'altern': 'Apprenticeship', 'apprenti': 'Apprenticeship'
            }
            df['job_type'] = df['job_type'].apply(lambda x: next(
                (job_type for term, job_type in job_type_map.items() 
                 if isinstance(x, str) and term in x.lower()), 
                x.capitalize() if isinstance(x, str) else x
            ))
        
        # Clean location data
        if 'location' in df.columns:
            df['location'] = df['location'].apply(
                lambda x: re.sub(r'\b(Remote|Hybrid|Télétravail|À distance)\b', '', x, 
                                flags=re.IGNORECASE).strip() if isinstance(x, str) else x
            )
        
        # Extract salary info
        if 'salary' in df.columns:
            salary_pattern = r'(\d[\d\s,.]*[€$£k]*\s*[-–]\s*\d[\d\s,.]*[€$£k]*|\d[\d\s,.]*[€$£k]+)'
            df['salary_cleaned'] = df['salary'].apply(
                lambda x: re.search(salary_pattern, x).group(0).strip() 
                if isinstance(x, str) and re.search(salary_pattern, x) else x
            )
        
        logging.info(f"Data cleaning completed. Final dataset has {len(df)} rows")
        return df
        
    except Exception as e:
        logging.error(f"Error during data cleaning: {str(e)}")
        raise

def analyze_job_data(jobs_df):
    """Perform basic analysis on the job data"""
    analysis = {
        'total_jobs': len(jobs_df)
    }
    
    # Add top values 
    for col, count in [('company', 5), ('location', 5), ('job_type', 10)]:
        if col in jobs_df.columns:
            analysis[f'top_{col}s'] = jobs_df[col].value_counts().head(count).to_dict()
    
    # Add date range if available
    if 'date_posted' in jobs_df.columns and not jobs_df['date_posted'].isna().all():
        analysis['date_range'] = {
            'newest': jobs_df['date_posted'].max().strftime('%Y-%m-%d') if not pd.isna(jobs_df['date_posted'].max()) else None,
            'oldest': jobs_df['date_posted'].min().strftime('%Y-%m-%d') if not pd.isna(jobs_df['date_posted'].min()) else None
        }
    
    return analysis

def save_data(jobs_df, base_filename):
    """Save job data to CSV format and return file object"""
    try:
        # Copy of the dataframe for export
        export_df = jobs_df.copy()
        
        # Convert datetime to string
        if 'date_posted' in export_df.columns and export_df['date_posted'].dtype == 'datetime64[ns]':
            export_df['date_posted'] = export_df['date_posted'].dt.strftime('%Y-%m-%d')
        
        # Save to CSV in memory
        csv_buffer = io.StringIO()
        export_df.to_csv(
            csv_buffer,
            quoting=csv.QUOTE_NONNUMERIC,
            escapechar="\\",
            index=False,
            encoding='utf-8'
        )
        csv_buffer.seek(0)
        
        # Create a discord file object
        csv_filename = f"{base_filename}.csv"
        discord_file = discord.File(
            fp=io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
            filename=csv_filename
        )
        
        logging.info(f"Successfully prepared job data as Discord file: {csv_filename}")
        return discord_file
    except Exception as e:
        logging.error(f"Error saving data: {str(e)}")
        raise

class JobSelectionView(discord.ui.View):
    def __init__(self, jobs, timeout=300):
        super().__init__(timeout=timeout)
        self.jobs = jobs
        self.add_item(JobSelect(jobs))

class JobSelect(discord.ui.Select):
    def __init__(self, jobs):
        # Limit options to 25 (Discord's limit)
        options = []
        for i, job in enumerate(jobs[:25]):
            job_title = f"{job['title']} - {job['company']}"
            if len(job_title) > 100:
                job_title = job_title[:97] + "..."
            options.append(
                discord.SelectOption(
                    label=job_title,
                    value=str(i),
                    description=f"{job['location']} - {job['job_type'] if 'job_type' in job else 'N/A'}"[:100]
                )
            )
        
        super().__init__(placeholder="Sélectionner une offre pour plus de détails", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        job = self.view.jobs[index]
        
        embed = discord.Embed(
            title=job['title'],
            url=job['job_url'],
            color=discord.Color.blue()
        )
        embed.add_field(name="Entreprise", value=job['company'], inline=True)
        embed.add_field(name="Lieu", value=job['location'], inline=True)
        
        if 'job_type' in job:
            embed.add_field(name="Type", value=job['job_type'], inline=True)
        
        if 'salary' in job and job['salary']:
            embed.add_field(name="Salaire", value=job['salary'], inline=True)
        
        if 'date_posted' in job:
            date_str = job['date_posted']
            if isinstance(date_str, str):
                embed.add_field(name="Date de publication", value=date_str, inline=True)
        
        if 'description' in job and job['description']:
            # Limiter la description à 1024 caractères max (limite Discord)
            description = job['description'][:1021] + "..." if len(job['description']) > 1024 else job['description']
            embed.add_field(name="Description", value=description, inline=False)
        
        embed.set_footer(text=f"Source: {job.get('job_site', 'Indeed')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# La classe à enregistrer comme Cog
class JobScraperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        configure_logging()
    
    @app_commands.command(name="scrape_internship", description="Rechercher des offres de stage ou d'alternance dans le domaine de la data")
    @app_commands.describe(
        search_term="Les termes de recherche (ex: data scientist, data analyst)",
        job_type="Type d'emploi à rechercher (stage, alternance, etc.)",
        location="Emplacement de recherche (ex: Paris, France)",
        max_results="Nombre maximum de résultats (max 100)",
        hours_old="Âge maximal des offres en heures"
    )
    async def scrape_internship(
        self, 
        interaction: discord.Interaction, 
        search_term: str,
        job_type: Optional[str] = "alternance",
        location: Optional[str] = "France",
        max_results: Optional[int] = 20,
        hours_old: Optional[int] = 72
    ):
        # Limiter le nombre max de résultats pour éviter de surcharger Discord et l'API
        if max_results > 100:
            max_results = 100
        
        await interaction.response.defer(thinking=True)
        
        try:
            # Construire la requête de recherche
            combined_search = f'"{job_type}" AND ("{search_term}")'
            
            # Paramètres de recherche
            search_params = {
                'site_names': ["indeed"],
                'search_term': combined_search,
                'location': location,
                'results_wanted': max_results,
                'hours_old': hours_old,
                'country_indeed': 'France' if location.lower() == "france" else None
            }
            
            # Faire le scraping de manière asynchrone
            jobs_df = await self.bot.loop.run_in_executor(None, scrape_job_listings, search_params)
            
            if len(jobs_df) == 0:
                await interaction.followup.send("Aucune offre trouvée avec ces critères.")
                return
            
            # Nettoyer les données
            cleaned_jobs = await self.bot.loop.run_in_executor(None, clean_job_data, jobs_df)
            
            # Analyser les données
            analysis = await self.bot.loop.run_in_executor(None, analyze_job_data, cleaned_jobs)
            
            # Convertir en dictionnaire pour la sélection
            jobs_list = cleaned_jobs.to_dict('records')
            
            # Créer un embed avec les résultats
            embed = discord.Embed(
                title=f"Offres trouvées pour '{search_term}' ({job_type})",
                description=f"Résultats pour {location} - {len(cleaned_jobs)} offres trouvées",
                color=discord.Color.green()
            )
            
            # Ajouter les principales statistiques
            if 'top_companies' in analysis:
                companies = ", ".join([f"{company} ({count})" for company, count in list(analysis['top_companies'].items())[:5]])
                embed.add_field(name="Top entreprises", value=companies, inline=False)
            
            if 'top_locations' in analysis:
                locations = ", ".join([f"{loc} ({count})" for loc, count in list(analysis['top_locations'].items())[:5]])
                embed.add_field(name="Top localisations", value=locations, inline=False)
            
            if 'top_job_types' in analysis:
                job_types = ", ".join([f"{jtype} ({count})" for jtype, count in list(analysis['top_job_types'].items())[:3]])
                embed.add_field(name="Types d'emploi", value=job_types, inline=False)
            
            # Créer un fichier CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"jobs_{timestamp}"
            csv_file = await self.bot.loop.run_in_executor(None, save_data, cleaned_jobs, base_filename)
            
            # Vue pour sélectionner des offres
            view = JobSelectionView(jobs_list)
            
            # Envoyer la réponse
            await interaction.followup.send(
                content=f"📊 Analyse complète des offres pour '{search_term}' ({job_type}) :",
                embed=embed, 
                file=csv_file,
                view=view
            )
            
        except Exception as e:
            logging.error(f"Error in scrape_internship command: {str(e)}")
            await interaction.followup.send(f"❌ Une erreur s'est produite lors de la recherche : {str(e)[:1900]}")

# Cette fonction est appelée par bot.py - conservez exactement ce nom
async def setup_internship_command(bot):
    await bot.add_cog(JobScraperCog(bot))