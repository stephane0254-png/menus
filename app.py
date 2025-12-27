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

def get_date_for_day(annee, semaine, jour_nom):
    """Calcule la date (JJ/MM) pour un jour donné d'une semaine précise"""
    jours_map = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    # On crée une date à partir du premier jour de l'année + le nombre de semaines
    d = datetime.date(annee, 1, 4) # Le 4 janvier est toujours dans la semaine 1
    d = d + datetime.timedelta(weeks=semaine-1)
    # On ajuste pour tomber sur le bon lundi
    d = d - datetime.timedelta(days=d.weekday())
    # On ajoute l'index du jour souhaité
    target_date = d + datetime.timedelta(days=jours_map.index(jour_nom))
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
        for jour in jours:
            date_str = get_date_for_day(sel_annee, int(sel_sem), jour)
            st.subheader(f"{jour} {date_str}")
            col_m, col_s = st.columns(2)
            
            df = load_data()
            exist_m = df[(df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem) & (df['Jour'] == jour) & (df['Moment'] == "Midi")]['Menu'].values
            exist_s = df[(df['Annee'] == sel_annee) & (df['Semaine'] == sel_sem) & (df['Jour'] == jour) & (df['Moment'] == "Soir")]['Menu'].values
            
            val_m = col_m.text_input(f"Midi ({jour})", value=exist_m[0] if len(exist_m) > 0 else "", key=f"m_{jour}")
            val_s = col_s.text_input(f"Soir ({jour})", value=exist_s[0] if len(exist_s) > 0 else "", key=f"s_{jour}")
            
            nouvelles_donnees.append([sel_annee, sel_sem, jour, "Midi", val_m])
            nouvelles_donnees.append([sel_annee, sel_sem, jour, "Soir", val_s])
            
        submit = st.form_submit_button("Enregistrer les menus")
        
        if submit:
            df = load_data()
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
        archives = df[['Annee', 'Semaine']].drop_duplicates().sort_values(['Annee', 'Semaine'], ascending=False)
        for _, row in archives.iterrows():
            if st.button(f"Voir Semaine {row['Semaine']} - {row['Annee']}"):
                df_hist = df[(df['Annee'] == row['Annee']) & (df['Semaine'] == row['Semaine'])]
                # On prépare le tableau avec les dates pour l'historique aussi
                df_hist['Jour_Date'] = df_hist.apply(lambda x: f"{x['Jour']} {get_date_for_day(x['Annee'], x['Semaine'], x['Jour'])}", axis=1)
                pivot_df = df_hist.pivot(index='Jour_Date', columns='Moment', values='Menu')
                # Trier selon l'ordre des jours de la semaine
                ordre_jours_date = [f"{j} {get_date_for_day(row['Annee'], row['Semaine'], j)}" for j in jours]
                st.table(pivot_df.reindex(ordre_jours_date))
    else:
        st.write("L'historique est vide.")
