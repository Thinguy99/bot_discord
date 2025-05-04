import discord
from discord import app_commands
from utils.helper import get_user_data

class OffreSelectionView(discord.ui.View):
    def __init__(self, offres):
        super().__init__(timeout=300)
        self.offres = offres
        select = OffreSelect(offres)
        self.add_item(select)

class OffreSelect(discord.ui.Select):
    def __init__(self, offres):
        options = [
    discord.SelectOption(
        label=(f"{i+1}. {offre['titre']} - {offre['entreprise']}")[:100],  # coupe à 100 caractères
        value=str(i)
    )
    for i, offre in enumerate(offres)
]

        super().__init__(placeholder="Sélectionner une offre pour l'analyser", options=options)

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        offre = self.view.offres[index]
        user = get_user_data(interaction.user.id)
        user.job_offer = offre

        embed = discord.Embed(
            title="Offre sélectionnée",
            description=(
                f"Vous avez sélectionné: {offre['titre']} - {offre['entreprise']}\n"
                f"Pour comparer avec votre CV, utilisez la commande `/comparer_cv_offre`\n"
                f"Pour générer une lettre de motivation, utilisez `/generer_lettre`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

def setup_scrape_command(bot):
    @bot.tree.command(name="scrape", description="Rechercher des offres d'emploi")
    async def scrape(interaction: discord.Interaction, termes: str, lieu: str = None):
        await interaction.response.defer()

        try:
            from scraping_group2 import FranceTravailAPI
            api = FranceTravailAPI()
            resultats = api.recherche_offres(ville_input=lieu or "Paris", mots_cles=termes)

            if "erreur" in resultats:
                await interaction.followup.send(f"❌ Erreur : {resultats['erreur'][:1900]}")
                return
            elif "message" in resultats:
                await interaction.followup.send(f"ℹ️ {resultats['message'][:1900]}")
                return

            offres = resultats["offres"]

            embed = discord.Embed(
                title=f"Offres d'emploi pour '{termes}'",
                description=f"Résultats pour {resultats['ville']} - {len(offres)} offres trouvées",
                color=discord.Color.blue()
            )

            total_chars = len(embed.title) + len(embed.description)
            max_fields = 0

            for i, offre in enumerate(offres):
                titre = f"{i+1}. {offre['titre']} - {offre['entreprise']}"
                if len(titre) > 256:
                    titre = titre[:253] + "..."

                lien = f"https://candidat.francetravail.fr/offres/recherche/detail/{offre.get('id', '')}"
                description = (
                    f"📍 {offre['lieu']}\n"
                    f"📝 {offre['contrat']}\n"
                    f"🔗 [Voir l'annonce sur France Travail]({lien})"
                )
                if len(description) > 1024:
                    description = description[:1021] + "..."

                if total_chars + len(titre) + len(description) > 5800 or max_fields >= 25:
                    break

                embed.add_field(name=titre, value=description, inline=False)
                total_chars += len(titre) + len(description)
                max_fields += 1

            if max_fields < len(offres):
                embed.set_footer(text=f"⚠️ {len(offres) - max_fields} offres non affichées (limite Discord atteinte)")

            view = OffreSelectionView(offres[:max_fields])
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            print(f"Erreur lors du scraping: {e}")
            await interaction.followup.send(
                f"❌ Une erreur est survenue : {str(e)[:1900]}",
                ephemeral=True
            )
