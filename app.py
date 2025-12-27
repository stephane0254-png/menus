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
    try:
        # ISO week date logic
        date_jan4 = datetime.date(int(annee), 1, 4)
        lundi_semaine_1 = date_jan4 - datetime.timedelta(days=date_jan4.weekday())
        target_date = lundi_semaine_1 + datetime.timedelta(weeks=int(semaine)-1, days=jours_map.index(jour_nom))
        return target_date.strftime("%d/%m")
    except:
        return "??"

# --- INTERFACE ---
st.title("🍴 Planning des Menus Familiaux")

tab1, tab2, tab3 = st.tabs(["📅 Semaines à venir", "📝 Saisir / Modifier", "📜 Historique"])

jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
moments = ["Midi", "Soir"]

# --- ONGLET 1 : AFFICHAGE SEMAINE EN COURS ET SUIVANTES ---
with tab1:
    today = datetime.date.today()
    annee_actuelle = today.year
    semaine_actuelle = today.isocalendar()[1]
    
    df = load_data()
    
    # On récupère toutes les semaines renseignées >= semaine actuelle
    if not df.empty:
        futures_semaines = df[
            ((df['Annee'] == annee_actuelle) & (df['Semaine'] >= semaine_actuelle)) | 
            (df['Annee'] > annee_actuelle)
        ][['Annee', 'Semaine']].drop_duplicates().sort_values(['Annee', 'Semaine'])
    else:
        futures_semaines = pd.DataFrame()

    if futures_semaines.empty:
        st.info(f"Aucun menu renseigné à partir de la semaine {semaine_actuelle}.")
    else:
        for _, row in futures_semaines.iterrows():
            ann, sem = int(row['Annee']), int(row['Semaine'])
            label = f"Semaine {sem} ({ann})"
            if sem == semaine_actuelle and ann == annee_actuelle:
                label += " - EN COURS"
            
            st.header(label)
            df_semaine = df[(df['Annee'] == ann) & (df['Semaine'] == sem)]
            
            for jour in jours:
                date_str = get_date_for_day(ann, sem, jour)
                # On n'affiche que si au moins un des deux moments est rempli
                menu_jour = df_semaine[df_semaine['Jour'] == jour]
                if not menu_jour['Menu'].dropna().str.strip().eq("").all():
                    with st.expander(f"**{jour} {date_str}**", expanded=True):
                        col1, col2 = st.columns(2)
                        for m in moments:
                            val = menu_jour[menu_jour['Moment'] == m]['Menu'].values
                            txt = val[0] if len(val) > 0 and pd.notna(val[0]) and val[0].strip() != "" else "Rien de prévu"
                            if m == "Midi":
                                col1.markdown(f"**☀️ Midi :** {txt}")
                            else:
                                col2.markdown(f"**🌙 Soir :** {txt}")
            st.divider()

# --- ONGLET 2 : SAISIR / MODIFIER ---
with tab2:
    st.header("Gestion des menus")
    
    # Initialisation de l'état pour la navigation si non présent
    if 'sel_semaine' not in st.session_state:
        st.session_state.sel_semaine = datetime.date.today().isocalendar()[1]
    if 'sel_annee' not in st.session_state:
        st.session_state.sel_annee = datetime.date.today().year

    # Boutons de navigation
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 2, 2, 1])
    
    if nav_col1.button("⬅️ Précédente"):
        if st.session_state.sel_semaine == 1:
            st.session_state.sel_semaine = 52
            st.session_state.sel_annee -= 1
        else:
            st.session_state.sel_semaine -= 1
        st.rerun()

    sel_annee = nav_col2.number_input("Année", value=st.session_state.sel_annee, step=1)
    sel_sem = nav_col3.number_input("Semaine", value=st.session_state.sel_semaine, min_value=1, max_value=53, step=1)
    
    # Mise à jour de l'état si saisie manuelle
    st.session_state.sel_annee = sel_annee
    st.session_state.sel_semaine = sel_sem

    if nav_col4.button("Suivante ➡️"):
        if st.session_state.sel_semaine >= 52:
            st.session_state.sel_semaine = 1
            st.session_state.sel_annee += 1
        else:
            st.session_state.sel_semaine += 1
        st.rerun()
    
    st.divider()

    df_actuel = load_data()
    
    with st.form("form_saisie", clear_on_submit=False):
        dict_saisie = {}
        for jour in jours:
            date_str = get_date_for_day(sel_annee, sel_sem, jour)
            st.subheader(f"{jour} {date_str}")
            col_m, col_s = st.columns(2)
            
            val_m_exist = ""
            val_s_exist = ""
            
            if not df_actuel.empty:
                m_data = df_actuel[(df_actuel['Annee'] == sel_annee) & (df_actuel['Semaine'] == sel_sem) & (df_actuel['Jour'] == jour) & (df_actuel['Moment'] == "Midi")]['Menu'].values
                s_data = df_actuel[(df_actuel['Annee'] == sel_annee) & (df_actuel['Semaine'] == sel_sem) & (df_actuel['Jour'] == jour) & (df_actuel['Moment'] == "Soir")]['Menu'].values
                if len(m_data) > 0 and pd.notna(m_data[0]): val_m_exist = m_data[0]
                if len(s_data) > 0 and pd.notna(s_data[0]): val_s_exist = s_data[0]
            
            dict_saisie[f"{jour}_Midi"] = col_m.text_input(f"Midi ({jour})", value=val_m_exist, key=f"in_m_{sel_annee}_{sel_sem}_{jour}")
            dict_saisie[f"{jour}_Soir"] = col_s.text_input(f"Soir ({jour})", value=val_s_exist, key=f"in_s_{sel_annee}_{sel_sem}_{jour}")
            
        submit = st.form_submit_button("Enregistrer les menus")
        
        if submit:
            if config_ok:
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
                st.rerun()
            else:
                st.error("Configuration GitHub manquante.")

# --- ONGLET 3 : HISTORIQUE ---
with tab3:
    st.header("Archives")
    df = load_data()
    if not df.empty and len(df) > 0:
        archives = df[['Annee', 'Semaine']].drop_duplicates().sort_values(['Annee', 'Semaine'], ascending=False)
        for _, row in archives.iterrows():
            if st.button(f"Voir Semaine {int(row['Semaine'])} - {int(row['Annee'])}", key=f"hist_{row['Annee']}_{row['Semaine']}"):
                df_hist = df[(df['Annee'] == row['Annee']) & (df['Semaine'] == row['Semaine'])]
                df_hist['Jour_Date'] = df_hist.apply(lambda x: f"{x['Jour']} {get_date_for_day(x['Annee'], x['Semaine'], x['Jour'])}", axis=1)
                pivot_df = df_hist.pivot(index='Jour_Date', columns='Moment', values='Menu')
                ordre_jours_date = [f"{j} {get_date_for_day(row['Annee'], row['Semaine'], j)}" for j in jours]
                st.table(pivot_df.reindex(ordre_jours_date))
    else:
        st.write("L'historique est vide.")
