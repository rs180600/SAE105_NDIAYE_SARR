import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

try:
   # 1. Charger les données
   print("Chargement des données...")
   
   # Précipitations
   precipitations = pd.read_csv('/home/Etudiants/RT/BUT-RT-1/rs180600/Bureau/Q_01_previous-1950-2023_RR-T-Vent.csv', delimiter=';')

   # Stations (depuis le JSON)
   import json
   with open('/home/Etudiants/RT/BUT-RT-1/rs180600/Bureau/fiches.json', 'r', encoding='utf-8') as f:
       geojson_data = json.load(f)

   # 2. Préparer les données des stations
   stations = []
   for feature in geojson_data['features']:
       properties = feature['properties']
       geometry = feature['geometry']
       stations.append({
           "Commune": properties["COMMUNE"],
           "Numéro Poste": properties["NUM_POSTE"],
           "Altitude": properties["ALTI"],
           "Nom Usuel": properties["NOM_USUEL"],
           "Latitude": geometry["coordinates"][1],
           "Longitude": geometry["coordinates"][0]
       })

   stations_df = pd.DataFrame(stations)

   # 3. Préparer les données de précipitations
   colonnes_precipitations = [
       'NUM_POSTE', 'NOM_USUEL', 'LAT', 'LON', 'ALTI',
       'AAAAMMJJ', 'RR', 'QRR'
   ]

   precipitations_df = precipitations[colonnes_precipitations].copy()
   precipitations_df['Date'] = pd.to_datetime(precipitations_df['AAAAMMJJ'], format='%Y%m%d')
   precipitations_df = precipitations_df.drop(columns=['AAAAMMJJ'])

   def trouver_periodes_pluvieuses(donnees, num_poste, duree_jours):
       """
       Trouve les périodes les plus pluvieuses pour une station donnée
       """
       # Filtrer pour la station spécifique et trier par date
       station_data = donnees[donnees['NUM_POSTE'] == num_poste].copy()
       station_data = station_data.sort_values('Date')
       
       # Calculer la somme mobile
       station_data['cumul_mobile'] = station_data['RR'].rolling(
           window=duree_jours, 
           min_periods=duree_jours
       ).sum()
       
       # Trouver les 5 périodes les plus pluvieuses
       periodes_pluvieuses = []
       station_data_temp = station_data.copy()
       
       for _ in range(5):
           if station_data_temp['cumul_mobile'].max() > 0:
               # Trouver l'index de la valeur maximale
               max_idx = station_data_temp['cumul_mobile'].idxmax()
               
               # Obtenir les dates de début et de fin
               date_fin = station_data_temp.loc[max_idx, 'Date']
               date_debut = date_fin - pd.Timedelta(days=duree_jours-1)
               
               # Ajouter la période aux résultats
               periodes_pluvieuses.append({
                   'Station': num_poste,
                   'Début': date_debut,
                   'Fin': date_fin,
                   'Cumul (mm)': station_data_temp.loc[max_idx, 'cumul_mobile']
               })
               
               # Masquer cette période pour la prochaine itération
               mask = (station_data_temp['Date'] >= date_debut) & (station_data_temp['Date'] <= date_fin)
               station_data_temp.loc[mask, 'RR'] = 0
               station_data_temp['cumul_mobile'] = station_data_temp['RR'].rolling(
                   window=duree_jours, 
                   min_periods=duree_jours
               ).sum()
       
       return pd.DataFrame(periodes_pluvieuses)

   def analyser_precipitations():
       print("\n=== Analyse des périodes pluvieuses ===")
       
       # Afficher les stations disponibles avec leurs noms 
       stations_info = precipitations_df[['NUM_POSTE', 'NOM_USUEL']].drop_duplicates()
       print("\nStations disponibles :")
       for _, station in stations_info.iterrows():
           print(f"N°{station['NUM_POSTE']} - {station['NOM_USUEL']}")
       
       # Demander les paramètres
       while True:
           try:
               num_station = int(input("\nEntrez le numéro de la station : "))
               if num_station in precipitations_df['NUM_POSTE'].unique():
                   break
               print("Cette station n'existe pas dans les données.")
           except ValueError:
               print("Veuillez entrer un numéro valide.")
       
       while True:
           try:
               duree = int(input("Entrez la durée de la période (en jours) : "))
               if duree > 0:
                   break
               print("La durée doit être positive.")
           except ValueError:
               print("Veuillez entrer un nombre valide.")
       
       # Trouver les périodes pluvieuses
       resultats = trouver_periodes_pluvieuses(precipitations_df, num_station, duree)
       
       # Afficher les résultats
       if not resultats.empty:
           # Trouver le nom de la station et son altitude
           station_info = precipitations_df[precipitations_df['NUM_POSTE'] == num_station].iloc[0]
           print(f"\nStation : {station_info['NOM_USUEL']} (n°{num_station})")
           print(f"Altitude : {station_info['ALTI']} m")
           print(f"\nLes {len(resultats)} périodes les plus pluvieuses sur {duree} jours :")
           
           for idx, periode in resultats.iterrows():
               print(f"\nPériode {idx + 1}:")
               print(f"Du {periode['Début'].strftime('%d/%m/%Y')} au {periode['Fin'].strftime('%d/%m/%Y')}")
               print(f"Cumul : {periode['Cumul (mm)']:.1f} mm")
               print(f"Moyenne quotidienne : {(periode['Cumul (mm)'] / duree):.1f} mm/jour")
           
           # Visualiser les données avec un graphique
           station_data = precipitations_df[precipitations_df['NUM_POSTE'] == num_station]
           plt.figure(figsize=(12, 6))
           plt.plot(station_data['Date'], station_data['RR'], label='Précipitations quotidiennes')
           for idx, periode in resultats.iterrows():
               plt.axvspan(periode['Début'], periode['Fin'], color='red', alpha=0.3, label=f'Période {idx + 1}' if idx == 0 else "")
           plt.title(f"Précipitations pour la station {station_info['NOM_USUEL']} (n°{num_station})")
           plt.xlabel("Date")
           plt.ylabel("Précipitations (mm)")
           plt.legend()
           plt.grid(alpha=0.3)
           plt.ylim(0)
           plt.show()
       else:
           print("Aucune période pluvieuse trouvée pour cette station.")
       
       # Proposer une nouvelle analyse
       if input("\nVoulez-vous faire une autre analyse ? (o/n) : ").lower().startswith('o'):
           analyser_precipitations()

   print("Données chargées avec succès !")
   
   if __name__ == "__main__":
       analyser_precipitations()

except Exception as e:
   print(f"Une erreur s'est produite : {str(e)}")
