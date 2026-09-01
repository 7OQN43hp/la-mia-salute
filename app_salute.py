import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Configurazione della pagina web
st.set_page_config(page_title="Gestione Salute Privata", page_icon="🏥", layout="wide")

# Connessione al database locale
conn = sqlite3.connect("salute_privata.db", check_same_thread=False)
cursor = conn.cursor()

# Creazione delle tabelle necessarie per salvare i dati
cursor.execute('''CREATE TABLE IF NOT EXISTS anagrafica (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cognome TEXT, data_nascita TEXT, gruppo_sanguigno TEXT, allergie TEXT, contatti_emergenza TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS visite (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, specializzazione TEXT, medico TEXT, struttura TEXT, esito TEXT, note TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS terapie (id INTEGER PRIMARY KEY AUTOINCREMENT, farmaco TEXT, principio_attivo TEXT, forma TEXT, dosaggio_singolo TEXT, dosaggio_prendere REAL, frequenza TEXT, data_inizio TEXT, data_fine TEXT, scorta_attuale REAL, soglia_minima REAL, orario_promemoria TEXT, note TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS parametri (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, pressione_max INTEGER, pressione_min INTEGER, battiti INTEGER, glicemia INTEGER, peso REAL, note TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS scadenziario (id INTEGER PRIMARY KEY AUTOINCREMENT, data_futura TEXT, specializzazione TEXT, medico TEXT, structure TEXT, note TEXT)'''.replace("structure", "struttura"))
cursor.execute('''CREATE TABLE IF NOT EXISTS spese (id INTEGER PRIMARY KEY AUTOINCREMENT, data_spesa TEXT, descrizione TEXT, categoria TEXT, importo REAL, detraibile INTEGER, note TEXT)''')
conn.commit()

# Inizializza profilo se vuoto
cursor.execute("SELECT COUNT(*) FROM anagrafica")
if cursor.fetchone() == 0:
    cursor.execute("INSERT INTO anagrafica (nome, cognome, data_nascita, gruppo_sanguigno, allergie, contatti_emergenza) VALUES ('', '', '', 'Sconosciuto', '', '')")
    conn.commit()

# Funzione per creare i promemoria del telefono
def crea_file_ics(titolo, data_str, orario, nota):
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
        data_formattata = dt.strftime("%Y%m%d")
    except:
        data_formattata = datetime.now().strftime("%Y%m%d")
    ora_pulita = orario.replace(':', '') if orario else "0800"
    return f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:{titolo}\nDESCRIPTION:{nota}\nDTSTART:{data_formattata}T{ora_pulita}00\nEND:VEVENT\nEND:VCALENDAR"

# Titolo e configurazione fissa delle schede
st.title("🏥 Sistema Globale di Gestione Salute Privata")
t1, t2, t3, t4, t5, t6, t7 = st.tabs(["📋 Anagrafica", "🗂️ Storico Visite", "⏰ Scadenziario", "💊 Farmaci & Scorte", "📈 Parametri Vitali", "💶 Spese Mediche", "⚙️ Backup"])
# --- TAB 1: ANAGRAFICA ---
with t1:
    st.header("Profilo Personale e Dati Vitali")
    cursor.execute("SELECT * FROM anagrafica WHERE id = 1")
    p = cursor.fetchone()
    with st.form("f_anag"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome", value=p[1])
        cognome = col1.text_input("Cognome", value=p[2])
        dn = col1.text_input("Data di Nascita", value=p[3])
        grp = col2.selectbox("Gruppo Sanguigno", ["Sconosciuto","A+","A-","B+","B-","AB+","AB-","0+","0-"], index=["Sconosciuto","A+","A-","B+","B-","AB+","AB-","0+","0-"].index(p[4]))
        em = col2.text_area("Contatti Emergenza", value=p[6])
        al = st.text_area("Allergie / Patologie Croniche", value=p[5])
        if st.form_submit_button("💾 Salva Profilo"):
            cursor.execute("UPDATE anagrafica SET nome=?, cognome=?, data_nascita=?, gruppo_sanguigno=?, allergie=?, contatti_emergenza=? WHERE id=1", (nome, cognome, dn, grp, al, em))
            conn.commit()
            st.success("Profilo aggiornato!")
            st.rerun()

# --- TAB 2: STORICO VISITE ---
with t2:
    st.header("🗂️ Archivio Storico Visite ed Esami Effettuati")
    with st.expander("➕ Inserisci Nuova Visita Passata"):
        with st.form("f_vis", clear_on_submit=True):
            col1, col2 = st.columns(2)
            dt = col1.date_input("Data Controllo", datetime.today())
            sp = col1.text_input("Specializzazione (es. Cardiologia)")
            md = col1.text_input("Medico")
            st_pr = col2.text_input("Struttura sanitaria")
            es = col2.text_input("Esito / Diagnosi")
            nt = st.text_area("Note e Terapie consigliate")
            if st.form_submit_button("📥 Registra Visita"):
                cursor.execute("INSERT INTO visite (data, specializzazione, medico, struttura, esito, note) VALUES (?,?,?,?,?,?)", (dt.strftime("%d/%m/%Y"), sp, md, st_pr, es, nt))
                conn.commit()
                st.success("Registrata!")
                st.rerun()
                
    cursor.execute("SELECT id, data, specializzazione, medico, struttura, esito FROM visite ORDER BY id DESC")
    visite_salvate = cursor.fetchall()
    if visite_salvate:
        for v in visite_salvate:
            ci, cd = st.columns(2)
            ci.markdown(f"📅 **{v[1]}** - **{v[2]}** | Dr. {v[3]} presso {v[4]} | *Esito:* {v[5]}")
            if cd.button("🗑️ Rimuovi", key=f"del_vis_{v[0]}", type="primary"):
                cursor.execute("DELETE FROM visite WHERE id=?", (v[0],))
                conn.commit()
                st.rerun()
            st.divider()
    else:
        st.info("Nessuna visita passata in archivio.")
# --- TAB 3: SCADENZIARIO VISITE FUTURE ---
with t3:
    st.header("⏰ Scadenziario e Promemoria Prossime Visite")
    with st.expander("➕ Prenota / Inserisci Appuntamento Futuro"):
        with st.form("f_scad", clear_on_submit=True):
            c1, c2 = st.columns(2)
            dt_f = c1.date_input("Data Appuntamento", datetime.today() + timedelta(days=7))
            ora_f = c1.text_input("Ora Appuntamento (HH:MM)", "10:00")
            sp_f = c1.text_input("Specializzazione Visita")
            md_f = c2.text_input("Nome Medico")
            st_f = c2.text_input("Struttura / Clinica")
            nt_f = st.text_area("Note / Documenti da portare")
            if st.form_submit_button("📅 Inserisci nello Scadenziario"):
                cursor.execute("INSERT INTO scadenziario VALUES (NULL,?,?,?,?,?)", (dt_f.strftime("%d/%m/%Y"), sp_f, md_f, st_f, f"Ora: {ora_f} | {nt_f}"))
                conn.commit()
                st.success("Appuntamento memorizzato!")
                st.rerun()

    cursor.execute("SELECT id, data_futura, specializzazione, medico, struttura, note FROM scadenziario ORDER BY id ASC")
    scadenze = cursor.fetchall()
    if scadenze:
        for s in scadenze:
            try:
                data_v = datetime.strptime(s[1], "%d/%m/%Y").date()
                giorni_rimasti = (data_v - datetime.today().date()).days
            except:
                giorni_rimasti = 0
                
            ci, cc, cd = st.columns([4, 1, 1])
            with ci:
                if giorni_rimasti < 0:
                    st.markdown(f"🔴 **{s[1]}** (Scaduta da {-giorni_rimasti} gg) - **{s[2]}** | Dr. {s[3]} ({s[4]})")
                elif giorni_rimasti == 0:
                    st.markdown(f"🚨 **OGGI** - **{s[2]}** | Dr. {s[3]} ({s[4]})")
                else:
                    st.markdown(f"🟢 **{s[1]}** (Tra **{giorni_rimasti}** giorni) - **{s[2]}** | Dr. {s[3]} ({s[4]})")
                st.caption(f"📝 *Note:* {s[5]}")
            
            with cc:
                ics_v = crea_file_ics(f"Visita {s[2]}", s[1], "09:00", s[5])
                st.download_button("📱 Promemoria", ics_v, f"visita_{s[0]}.ics", "text/calendar", key=f"ics_v_{s[0]}")
            with cd:
                if st.button("🗑️ Sposta", key=f"del_scad_{s[0]}"):
                    cursor.execute("DELETE FROM scadenziario WHERE id=?", (s[0],))
                    conn.commit()
                    st.rerun()
            st.divider()
    else:
        st.info("Nessun appuntamento futuro in scadenziario.")

# --- TAB 4: FARMACI & SCORTE ---
with t4:
    st.header("💊 Registro Terapie e Gestione Scorte")
    with st.expander("➕ Aggiungi Farmaco nel Cassetto"):
        with st.form("f_farm", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            fr = c1.text_input("Nome Commerciale")
            pr = c1.text_input("Principio Attivo")
            fm = c1.selectbox("Forma", ["Pillole", "Capsule", "Fiale", "Gocce", "Bustine"])
            dg = c1.text_input("Dosaggio Singolo (es. 500mg)")
            dp = c2.number_input("Dose da prendere", min_value=0.1, value=1.0)
            fq = c2.text_input("Frequenza giornaliera")
            or_sv = c2.text_input("Ora Sveglia", "08:00")
            sc = c3.number_input("Scorta Iniziale (Pezzi totali)", min_value=0.0, value=20.0)
            sg = c3.number_input("Soglia Minima Allarme", min_value=0.0, value=5.0)
            di = c3.date_input("Inizio Cura")
            df = c3.date_input("Fine Cura")
            nt_f = st.text_area("Indicazioni d'uso")
            if st.form_submit_button("📥 Memorizza Medicina"):
                cursor.execute("INSERT INTO terapie VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)", (fr,pr,fm,dg,dp,fq,di.strftime("%d/%m/%Y"),df.strftime("%d/%m/%Y"),sc,sg,or_sv,nt_f))
                conn.commit()
                st.success("Salvato!")
                st.rerun()

    cursor.execute("SELECT id, farmaco, principio_attivo, forma, dosaggio_singolo, dosaggio_prendere, scorta_attuale, soglia_minima, orario_promemoria, note FROM terapie")
    for f in cursor.fetchall():
        warn = "⚠️ **SCORTA IN ESAURIMENTO!**" if f[6] <= f[7] else ""
        ci, ca, cc, cd = st.columns(4)
        ci.markdown(f"### {f[1]} *({f[2]})*\n🔹 Confezione: {f[3]} da {f[4]} | ⏰ Ore {f[8]} | 📦 In Casa: **{f[6]}** {warn}")
        if ca.button(f"👇 Presa dose ({f[5]})", key=f"tk_{f[0]}"):
            cursor.execute("UPDATE terapie SET scorta_attuale=? WHERE id=?", (max(0.0, f[6]-f[5]), f[0]))
            conn.commit()
            st.rerun()
        cc.download_button("📱 Sveglia", crea_file_ics(f"Prendere {f[1]}", datetime.now().strftime("%d/%m/%Y"), f[8], f[9]), f"sveglia_{f[0]}.ics", "text/calendar", key=f"ic_{f[0]}")
        if cd.button("🗑️ Elimina", key=f"dl_{f[0]}"):
            cursor.execute("DELETE FROM terapie WHERE id=?", (f[0],))
            conn.commit()
            st.rerun()
        st.divider()
# --- TAB 5: PARAMETRI VITALI ---
with t5:
    st.header("📈 Diario dei Parametri Vitali")
    with st.expander("➕ Registra Nuova Misurazione"):
        with st.form("f_par", clear_on_submit=True):
            col_d1, col_d2 = st.columns(2)
            d_pa = col_d1.date_input("Data")
            p_mx = col_d1.number_input("Pressione Max", value=120)
            p_mn = col_d1.number_input("Pressione Min", value=80)
            o_pa = col_d2.text_input("Ora", datetime.now().strftime("%H:%M"))
            bt = col_d2.number_input("Battiti (bpm)", value=70)
            gl = col_d2.number_input("Glicemia", value=0)
            ps = st.number_input("Peso (kg)", value=0.0)
            nt_p = st.text_area("Note fisiche")
            if st.form_submit_button("📥 Salva nel Diario"):
                cursor.execute("INSERT INTO parametri VALUES (NULL,?,?,?,?,?,?,?,?)", (d_pa.strftime("%Y-%m-%d"), o_pa, p_mx, p_mn, bt, gl, ps, nt_p))
                conn.commit()
                st.success("Registrato!")
                st.rerun()
                
    df = pd.read_sql_query("SELECT data, pressione_max as Max, pressione_min as Min, battiti as Battiti FROM parametri ORDER BY data ASC", conn)
    if not df.empty:
        st.line_chart(df.set_index('data')[['Max', 'Min', 'Battiti']])
        st.dataframe(df.sort_index(ascending=False), use_container_width=True, hide_index=True)

# --- TAB 6: GESTIONE SPESE MEDICHE ---
with t6:
    st.header("💶 Spese Mediche e Detrazioni (730)")
    with st.expander("➕ Registra una nuova Spesa"):
        with st.form("f_spese", clear_on_submit=True):
            cx1, cx2 = st.columns(2)
            dt_s = cx1.date_input("Data Pagamento", datetime.today())
            desc_s = cx1.text_input("Descrizione")
            cat_s = cx1.selectbox("Categoria Spesa", ["Farmaci / Ticket", "Visite Private", "Esami / Diagnostica", "Dispositivi Medici", "Altro"])
            imp_s = cx2.number_input("Importo (€)", min_value=0.01, value=15.00, step=0.01)
            detr_s = cx2.checkbox("Detraibile (19%)?", value=True)
            nt_s = cx2.text_area("Note")
            if st.form_submit_button("📥 Registra Spesa"):
                cursor.execute("INSERT INTO spese VALUES (NULL,?,?,?,?,?,?)", (dt_s.strftime("%Y-%m-%d"), desc_s, cat_s, imp_s, 1 if detr_s else 0, nt_s))
                conn.commit()
                st.success("Spesa registrata!")
                st.rerun()
                
    df_spese = pd.read_sql_query("SELECT id, data_spesa as Data, descrizione as Descrizione, categoria as Categoria, importo as 'Importo (€)', detraibile as Detraibile FROM spese ORDER BY data_spesa DESC", conn)
    if not df_spese.empty:
        tot = df_spese['Importo (€)'].sum()
        tot_det = df_spese[df_spese['Detraibile'] == 1]['Importo (€)'].sum()
        rimb = max(0.0, (tot_det - 129.11) * 0.19)
        c_b1, c_b2, c_b3 = st.columns(3)
        c_b1.metric("Totale Speso", f"€ {tot:.2f}")
        c_b2.metric("Detraibile", f"€ {tot_det:.2f}")
        c_b3.metric("Rimborso 730", f"€ {rimb:.2f}")
        st.dataframe(df_spese.drop(columns=['id']), use_container_width=True, hide_index=True)

# --- TAB 7: AREA BACKUP ---
with t7:
    st.header("⚙️ Area Sicurezza e Backup")
    try:
        with open("salute_privata.db", "rb") as f_db:
            st.download_button("📥 Scarica File Database (salute_privata.db)", f_db, "salute_privata.db", "application/x-sqlite3")
    except:
        st.info("Database ancora vuoto.")