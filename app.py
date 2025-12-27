import streamlit as st
import pandas as pd
import datetime
import os

# Configuration de la page
st.set_page_config(page_title="Menus de la Famille", layout="wide")

# Nom du fichier de données
DATA_FILE = "menus_famille.csv"

# Initialisation du fichier CSV s'il n'existe pas
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=['Annee', 'Semaine', 'Jour', 'Moment', 'Menu'])
    df_init.to_csv(DATA_FILE, index=False)

def load_data():
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- INTERFACE ---
st.title("🍴 Planning des Menus Familiaux")

tab1, tab2, tab3 = st.tabs(["📅 Semaine en cours", "📝 Saisir / Modifier", "📜 Historique"])

jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
moments = ["Midi", "Soir"]

# --- ONGLET 1 : AFFICHAGE SEMAINE EN COURS ---
with tab1:
    today = datetime.date.today()
    annee_actuelle = today.year
    semaine_actuelle = today.isocalendar()[1]
    
    st.header(f"Semaine {semaine_actuelle} ({annee_actuelle})")
    
    df = load_data()
    df_semaine = df[(df['Annee'] == annee_actuelle) & (df['Semaine'] == semaine_actuelle)]
    
    if df_semaine.empty:
        st.info("Aucun menu renseigné pour cette semaine.")
    else:
        for jour in jours:
            with st.expander(f"**{jour}**", expanded=True):
                col1, col2 = st.columns(2)
                for m in moments:
                    menu_text = df_semaine[(df_semaine['Jour'] == jour) & (df_semaine['Moment'] == m)]['Menu'].values
                    val = menu_text[0] if len(menu_text) > 0 else "Rien de prévu"
                    if m == "Midi":
                        col1.markdown(f"**☀️ Midi :** {val}")
                    else:
                        col2.markdown(f"**🌙 Soir :** {val}")

# --- ONGLET 2 : SAISIR / MODIFIER ---
with tab2:
    st.header("Gestion des menus")
    
    with st.form("form_saisie"):
        c1, c2 = st.columns(2)
        sel_annee = c1.number_input("Année", value=annee_actuelle, step=1)
        sel_sem = c2.number_input("Numéro de Semaine", value=semaine_actuelle, min_value=1, max_value=53, step=1)
        
        st.divider()
        
        # Création d'une grille de saisie
        nouvelles_donnees = []
        for jour in jours:
            st.subheader(jour)
            col_m, col_s = st.columns(2)
            
            # Récupérer les valeurs existantes si elles existent
            df = load_data()
            exist_m = df[(df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem) & (df['Jour'] == jour) & (df['Moment'] == "Midi")]['Menu'].values
            exist_s = df[(df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem) & (df['Jour'] == jour) & (df['Moment'] == "Soir")]['Menu'].values
            
            val_m = col_m.text_input(f"Midi ({jour})", value=exist_m[0] if len(exist_m) > 0 else "")
            val_s = col_s.text_input(f"Soir ({jour})", value=exist_s[0] if len(exist_s) > 0 else "")
            
            nouvelles_donnees.append([sel_annee, sel_sem, jour, "Midi", val_m])
            nouvelles_donnees.append([sel_annee, sel_sem, jour, "Soir", val_s])
            
        submit = st.form_submit_button("Enregistrer les menus")
        
        if submit:
            df = load_data()
            # Supprimer les anciennes entrées pour cette semaine avant de sauvegarder les nouvelles
            df = df[~((df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem))]
            
            new_df = pd.DataFrame(nouvelles_donnees, columns=['Annee', 'Semaine', 'Jour', 'Moment', 'Menu'])
            df = pd.concat([df, new_df], ignore_index=True)
            
            save_data(df)
            st.success(f"Menus de la semaine {sel_sem} enregistrés !")

# --- ONGLET 3 : HISTORIQUE ---
with tab3:
    st.header("Archives")
    df = load_data()
    if not df.empty:
        # Liste des semaines disponibles
        archives = df[['Annee', 'Semaine']].drop_duplicates().sort_values(['Annee', 'Semaine'], ascending=False)
        for _, row in archives.iterrows():
            if st.button(f"Voir Semaine {row['Semaine']} - {row['Annee']}"):
                df_hist = df[(df['Annee'] == row['Annee']) & (df['Semaine'] == row['Semaine'])]
                st.table(df_hist.pivot(index='Jour', columns='Moment', values='Menu').reindex(jours))
    else:
        st.write("L'historique est vide.")
