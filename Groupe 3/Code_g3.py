#Message pour les autres groupes : Pour utiliser le code, vous devez installer dans votre console : 
#' !pip install python-jobspy ' (sans cette installation, le code ne fonctionnera pas)
# ensuite vous pouvez lancer le code : python votre_nom_de_fichier.py (ex: python scrap.py)

import csv
import json
import logging
from datetime import datetime
from jobspy import scrape_jobs
import pandas as pd
import sys
import re

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
        print("❌ Une erreur est survenue pendant le scraping. Consultez le fichier de log pour plus de détails.")
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
    """Save job data to CSV, JSON, and Python dictionary formats"""
    try:
        # Copy of the dataframe for export
        export_df = jobs_df.copy()
        
        # Convert datetime to string
        if 'date_posted' in export_df.columns and export_df['date_posted'].dtype == 'datetime64[ns]':
            export_df['date_posted'] = export_df['date_posted'].dt.strftime('%Y-%m-%d')
        
        # Save CSV
        csv_filename = f"{base_filename}.csv"
        export_df.to_csv(
            csv_filename,
            quoting=csv.QUOTE_NONNUMERIC,
            escapechar="\\",
            index=False,
            encoding='utf-8'
        )
        
        # Save JSON
        json_filename = f"{base_filename}.json"
        jobs_records = export_df.to_dict(orient='records')
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(jobs_records, f, ensure_ascii=False, indent=2)
        
        # Python dictionary
        dict_filename = f"{base_filename}_dict.py"
        with open(dict_filename, 'w', encoding='utf-8') as f:
            f.write("job_data = [\n")
            for job in jobs_records:
                f.write("    {\n")
                for key, value in job.items():
                    if isinstance(value, str):
                        formatted_value = f'"{value}"'
                    elif value is None:
                        formatted_value = 'None'
                    else:
                        formatted_value = str(value)
                    f.write(f'        "{key}": {formatted_value},\n')
                f.write("    },\n")
            f.write("]\n")
            
        logging.info(f"Successfully saved job data to {csv_filename}, {json_filename}, and {dict_filename}")
        return csv_filename, json_filename, dict_filename
    except Exception as e:
        logging.error(f"Error saving data: {str(e)}")
        raise

def main():
    """Main function to execute the job scraping workflow"""
    configure_logging()

    # Search parameters
    search_params = {
        'site_names': ["indeed"],
        'search_term': '"alternance" AND ("data scientist" OR "data science" OR "data analyst" OR "data analyse" OR "quantitative" OR "statisticien")',
        'location': "France",
        'results_wanted': 200,
        'hours_old': 72,
        'country_indeed': 'France'
    }

    try:
        jobs = scrape_job_listings(search_params)
        cleaned_jobs = clean_job_data(jobs)
        analysis = analyze_job_data(cleaned_jobs)
        
        # Log analysis results
        logging.info("\nJob Data Analysis Results:")
        for key, value in analysis.items():
            if isinstance(value, dict):
                logging.info(f"{key.replace('_', ' ').title()}:")
                for subkey, subvalue in value.items():
                    logging.info(f"  - {subkey}: {subvalue}")
            else:
                logging.info(f"{key.replace('_', ' ').title()}: {value}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"jobs_{timestamp}"
        csv_file, json_file, dict_file = save_data(cleaned_jobs, base_filename)

        # Data and summary
        logging.info("\nSample Cleaned Job Data:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        logging.info(cleaned_jobs.head(3).to_string())

        print(f"\nJob scraping completed successfully!")
        print(f"- Total jobs scraped: {analysis['total_jobs']}")
        print(f"- Data saved to: {csv_file}, {json_file}, and {dict_file}")

    except Exception as e:
        logging.error(f"Script failed: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
