import streamlit as st
import pandas as pd
import datetime
import os
from github import Github

# Configuration de la page
st.set_page_config(page_title="Menus de la Famille", layout="wide")

# Configuration GitHub (Récupérée depuis les Secrets Streamlit)
try:
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["REPO_NAME"]
    g = Github(token)
    repo = g.get_repo(repo_name)
except:
    st.error("Configuration GitHub manquante dans les Secrets Streamlit.")

DATA_FILE = "menus_famille.csv"

def load_data():
    # On essaie de lire le fichier sur GitHub pour être sûr d'avoir la version la plus récente
    try:
        content = repo.get_contents(DATA_FILE)
        return pd.read_csv(content.download_url)
    except:
        if os.path.exists(DATA_FILE):
            return pd.read_csv(DATA_FILE)
        return pd.DataFrame(columns=['Annee', 'Semaine', 'Jour', 'Moment', 'Menu'])

def save_to_github(df):
    csv_content = df.to_csv(index=False)
    try:
        contents = repo.get_contents(DATA_FILE)
        repo.update_file(DATA_FILE, "Mise à jour des menus", csv_content, contents.sha)
        st.success("Sauvegarde permanente réussie sur GitHub !")
    except Exception as e:
        # Si le fichier n'existe pas encore sur GitHub
        repo.create_file(DATA_FILE, "Création du fichier menus", csv_content)
        st.success("Fichier créé et sauvegardé sur GitHub !")

def get_date_for_day(annee, semaine, jour_nom):
    jours_map = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    premiere_date = datetime.date(annee, 1, 4)
    lundi_semaine_1 = premiere_date - datetime.timedelta(days=premiere_date.weekday())
    target_date = lundi_semaine_1 + datetime.timedelta(weeks=semaine-1, days=jours_map.index(jour_nom))
    return target_date.strftime("%d/%m")

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
            date_str = get_date_for_day(annee_actuelle, semaine_actuelle, jour)
            with st.expander(f"**{jour} {date_str}**", expanded=True):
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
        
        nouvelles_donnees = []
        df_actuel = load_data()
        
        for jour in jours:
            date_str = get_date_for_day(int(sel_annee), int(sel_sem), jour)
            st.subheader(f"{jour} {date_str}")
            col_m, col_s = st.columns(2)
            
            exist_m = df_actuel[(df_actuel['Annee'] == sel_annee) & (df_actuel['Semaine'] == sel_sem) & (df_actuel['Jour'] == jour) & (df_actuel['Moment'] == "Midi")]['Menu'].values
            exist_s = df_actuel[(df_actuel['Annee'] == sel_annee) & (df_actuel['Semaine'] == sel_sem) & (df_actuel['Jour'] == jour) & (df_actuel['Moment'] == "Soir")]['Menu'].values
            
            val_m = col_m.text_input(f"Midi ({jour})", value=exist_m[0] if len(exist_m) > 0 else "", key=f"m_{jour}")
            val_s = col_s.text_input(f"Soir ({jour})", value=exist_s[0] if len(exist_s) > 0 else "", key=f"s_{jour}")
            
            nouvelles_donnees.append([sel_annee, sel_sem, jour, "Midi", val_m])
            nouvelles_donnees.append([sel_annee, sel_sem, jour, "Soir", val_s])
            
        submit = st.form_submit_button("Enregistrer les menus")
        
        if submit:
            df = load_data()
            df = df[~((df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem))]
            new_df = pd.DataFrame(nouvelles_donnees, columns=['Annee', 'Semaine', 'Jour', 'Moment', 'Menu'])
            df_final = pd.concat([df, new_df], ignore_index=True)
            save_to_github(df_final)

# --- ONGLET 3 : HISTORIQUE ---
with tab3:
    st.header("Archives")
    df = load_data()
    if not df.empty:
        archives = df[['Annee', 'Semaine']].drop_duplicates().sort_values(['Annee', 'Semaine'], ascending=False)
        for _, row in archives.iterrows():
            if st.button(f"Voir Semaine {row['Semaine']} - {row['Annee']}"):
                df_hist = df[(df['Annee'] == row['Annee']) & (df['Semaine'] == row['Semaine'])]
                df_hist['Jour_Date'] = df_hist.apply(lambda x: f"{x['Jour']} {get_date_for_day(int(x['Annee']), int(x['Semaine']), x['Jour'])}", axis=1)
                pivot_df = df_hist.pivot(index='Jour_Date', columns='Moment', values='Menu')
                ordre_jours_date = [f"{j} {get_date_for_day(int(row['Annee']), int(row['Semaine']), j)}" for j in jours]
                st.table(pivot_df.reindex(ordre_jours_date))
    else:
        st.write("L'historique est vide.")
