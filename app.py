import streamlit as st
import pandas as pd
import datetime
import os
from github import Github
import io

# Configuration de la page
st.set_page_config(page_title="Menus de la Famille", layout="wide")

# Initialisation sécurisée des secrets
try:
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["REPO_NAME"]
    g = Github(token)
    repo = g.get_repo(repo_name)
    config_ok = True
except Exception as e:
    config_ok = False
    st.warning("⚠️ Configuration GitHub en attente ou incorrecte dans les Secrets Streamlit.")

DATA_FILE = "menus_famille.csv"
COLUMNS = ['Annee', 'Semaine', 'Jour', 'Moment', 'Menu']

def load_data():
    if config_ok:
        try:
            content = repo.get_contents(DATA_FILE)
            decoded_content = content.decoded_content.decode('utf-8')
            return pd.read_csv(io.StringIO(decoded_content))
        except:
            return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(columns=COLUMNS)

def save_to_github(df):
    csv_content = df.to_csv(index=False)
    try:
        try:
            contents = repo.get_contents(DATA_FILE)
            repo.update_file(DATA_FILE, "Mise à jour des menus", csv_content, contents.sha)
        except:
            repo.create_file(DATA_FILE, "Création du fichier menus", csv_content)
        st.success("✅ Sauvegarde réussie sur GitHub !")
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde : {e}")

def get_date_for_day(annee, semaine, jour_nom):
    jours_map = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    premiere_date = datetime.date(int(annee), 1, 4)
    lundi_semaine_1 = premiere_date - datetime.timedelta(days=premiere_date.weekday())
    target_date = lundi_semaine_1 + datetime.timedelta(weeks=int(semaine)-1, days=jours_map.index(jour_nom))
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
    if not df.empty:
        df_semaine = df[(df['Annee'] == annee_actuelle) & (df['Semaine'] == semaine_actuelle)]
    else:
        df_semaine = pd.DataFrame()
    
    if df_semaine.empty:
        st.info("Aucun menu renseigné pour cette semaine.")
    else:
        for jour in jours:
            date_str = get_date_for_day(annee_actuelle, semaine_actuelle, jour)
            with st.expander(f"**{jour} {date_str}**", expanded=True):
                col1, col2 = st.columns(2)
                for m in moments:
                    menu_text = df_semaine[(df_semaine['Jour'] == jour) & (df_semaine['Moment'] == m)]['Menu'].values
                    val = menu_text[0] if len(menu_text) > 0 and pd.notna(menu_text[0]) else "Rien de prévu"
                    if m == "Midi":
                        col1.markdown(f"**☀️ Midi :** {val}")
                    else:
                        col2.markdown(f"**🌙 Soir :** {val}")

# --- ONGLET 2 : SAISIR / MODIFIER ---
with tab2:
    st.header("Gestion des menus")
    
    # Utilisation d'un formulaire pour regrouper toutes les saisies
    with st.form("form_saisie", clear_on_submit=False):
        c1, c2 = st.columns(2)
        sel_annee = c1.number_input("Année", value=annee_actuelle, step=1)
        sel_sem = c2.number_input("Numéro de Semaine", value=semaine_actuelle, min_value=1, max_value=53, step=1)
        
        st.divider()
        
        # On charge les données existantes une seule fois pour pré-remplir les champs
        df_actuel = load_data()
        
        dict_saisie = {}
        for jour in jours:
            date_str = get_date_for_day(sel_annee, sel_sem, jour)
            st.subheader(f"{jour} {date_str}")
            col_m, col_s = st.columns(2)
            
            exist_m = [""]
            exist_s = [""]
            if not df_actuel.empty:
                exist_m = df_actuel[(df_actuel['Annee'] == sel_annee) & (df_actuel['Semaine'] == sel_sem) & (df_actuel['Jour'] == jour) & (df_actuel['Moment'] == "Midi")]['Menu'].values
                exist_s = df_actuel[(df_actuel['Annee'] == sel_annee) & (df_actuel['Semaine'] == sel_sem) & (df_actuel['Jour'] == jour) & (df_actuel['Moment'] == "Soir")]['Menu'].values
            
            # Les champs de texte dans un formulaire ne déclenchent pas de mise à jour tant qu'on n'appuie pas sur le bouton
            dict_saisie[f"{jour}_Midi"] = col_m.text_input(f"Midi ({jour})", value=exist_m[0] if len(exist_m) > 0 and pd.notna(exist_m[0]) else "", key=f"m_{jour}")
            dict_saisie[f"{jour}_Soir"] = col_s.text_input(f"Soir ({jour})", value=exist_s[0] if len(exist_s) > 0 and pd.notna(exist_s[0]) else "", key=f"s_{jour}")
            
        submit = st.form_submit_button("Enregistrer les menus")
        
        if submit:
            if config_ok:
                # Préparation des nouvelles données à partir du dictionnaire de saisie
                nouvelles_donnees = []
                for jour in jours:
                    nouvelles_donnees.append([sel_annee, sel_sem, jour, "Midi", dict_saisie[f"{jour}_Midi"]])
                    nouvelles_donnees.append([sel_annee, sel_sem, jour, "Soir", dict_saisie[f"{jour}_Soir"]])
                
                df = load_data()
                if not df.empty:
                    df = df[~((df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem))]
                new_df = pd.DataFrame(nouvelles_donnees, columns=COLUMNS)
                df_final = pd.concat([df, new_df], ignore_index=True)
                save_to_github(df_final)
                # Petit rafraîchissement pour voir les changements
                st.rerun()
            else:
                st.error("Impossible d'enregistrer : la configuration GitHub est manquante.")

# --- ONGLET 3 : HISTORIQUE ---
with tab3:
    st.header("Archives")
    df = load_data()
    if not df.empty and len(df) > 0:
        archives = df[['Annee', 'Semaine']].drop_duplicates().sort_values(['Annee', 'Semaine'], ascending=False)
        for _, row in archives.iterrows():
            if st.button(f"Voir Semaine {int(row['Semaine'])} - {int(row['Annee'])}"):
                df_hist = df[(df['Annee'] == row['Annee']) & (df['Semaine'] == row['Semaine'])]
                df_hist['Jour_Date'] = df_hist.apply(lambda x: f"{x['Jour']} {get_date_for_day(x['Annee'], x['Semaine'], x['Jour'])}", axis=1)
                pivot_df = df_hist.pivot(index='Jour_Date', columns='Moment', values='Menu')
                ordre_jours_date = [f"{j} {get_date_for_day(row['Annee'], row['Semaine'], j)}" for j in jours]
                st.table(pivot_df.reindex(ordre_jours_date))
    else:
        st.write("L'historique est vide.")
