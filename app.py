# Back-end: elabora i dati, interagisce con lo storage e risponde alle richieste del browser
# Flask = micro-framework web per Python che fornisce gli strumenti e le funzionalità di base per costruire applicazioni web

from flask import Flask, request, render_template, send_file, abort, redirect, url_for
import pandas as pd
import os
from datetime import datetime
# import threading # Non più necessario se non si usa excel_lock per il file principale
import logging   # Importa il modulo logging
import requests  # Importa la libreria requests per le chiamate HTTP (necessaria per upload esterni)
import urllib.parse # Per codificare gli URL (utile per mailto)

# Inizializzazione dell'applicazione Flask
app = Flask(__name__)

# Configura il logging: imposta il livello minimo dei messaggi da visualizzare (INFO e superiori)
# e il formato del messaggio (timestamp, livello, messaggio).
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# File Excel principale dove verranno salvate tutte le risposte
# EXCEL_FILE = "alten_skills_trial.xlsx" # Non più usato per salvataggio principale
# Nome della directory dove verranno salvati i file Excel individuali per ogni utente
USER_FILES_DIR = "skills_user"


EMAIL_ONLY_MODE = os.environ.get("EMAIL_ONLY_MODE", "False").lower() == "false"
# Crea un oggetto Lock per gestire l'accesso concorrente al file Excel principale
# excel_lock = threading.Lock() # Non più necessario se non si usa excel_lock per il file principale

# Crea la directory USER_FILES_DIR se non esiste già dove exist_ok=True evita un errore se la directory esiste già
os.makedirs(USER_FILES_DIR, exist_ok=True)

# Funzione per inizializzare o verificare il file Excel principale (VERSIONE ROBUSTA)
# Questa funzione non è più necessaria se non si usa il file Excel principale
# def initialize_main_excel_file():
#     global EXCEL_FILE
#     logging.info(f"Tentativo di inizializzazione del file Excel principale: {EXCEL_FILE}")
    
#     required_columns = [
#         "ID", "Nome", "Email", "Istruzione", "Indirizzo di studio", "Sede Alten",
#         "Esperienza (anni)", "Esperienza Alten (anni)", "Certificazioni",
#         "Clienti Railway", "Area Railway", "Normative", "Metodologie lavoro",
#         "Sistemi Operativi", "Info aggiuntive", "Hobby"
#     ]

#     try:
#         df = pd.read_excel(EXCEL_FILE)
#         logging.info(f"File Excel '{EXCEL_FILE}' caricato con {len(df)} righe.")
        
#         if df.empty or not all(col in df.columns for col in required_columns):
#             logging.warning(f"Il file Excel '{EXCEL_FILE}' è vuoto o mancano colonne essenziali. Lo si reinizializza con le intestazioni predefinite.")
#             df = pd.DataFrame(columns=required_columns)
#             df.to_excel(EXCEL_FILE, index=False)
#             logging.info(f"File Excel '{EXCEL_FILE}' reinizializzato con intestazioni.")
        
#     except FileNotFoundError:
#         logging.info(f"File Excel '{EXCEL_FILE}' non trovato. Creazione di un nuovo file con intestazioni.")
#         df = pd.DataFrame(columns=required_columns)
#         df.to_excel(EXCEL_FILE, index=False)
#         logging.info(f"File Excel '{EXCEL_FILE}' creato con successo.")
#     except Exception as e:
#         logging.error(f"Errore critico durante il caricamento o la creazione del file Excel '{EXCEL_FILE}': {e}. Il file verrà creato vuoto per proseguire.")
#         df = pd.DataFrame(columns=required_columns)
#         df.to_excel(EXCEL_FILE, index=False)
#         logging.warning(f"Recupero: creato un file Excel vuoto per '{EXCEL_FILE}' a causa di un errore precedente.")

# Chiamiamo la funzione di inizializzazione all'avvio dell'applicazione.
# initialize_main_excel_file() # Non più necessario

# Funzione per assegnare un nuovo ID a ciascun nuovo utente che compila il Form
# L'ID sarà solo sequenziale per i nomi dei file temporanei, non persistente nel file principale
_current_id = 0
def get_next_id():
    global _current_id
    _current_id += 1
    return _current_id

# Funzione per aggiungere le informazioni delle sezioni di progetto in ordine logico
def aggiungi_sezione(nome_sezione, scelte, dettagli_dict, data):
    data[f"Aree progetti {nome_sezione}"] = ", ".join(scelte)
    for area in dettagli_dict:
        if area in dettagli_dict:
            data[area] = "\n\n".join(dettagli_dict[area]) if dettagli_dict[area] else ""
        else:
            data[area] = ""

# --- CONFIGURAZIONE MODALITÀ FASE E-MAIL/SHAREPOINT ---
# Imposta su 'True' per la modalità solo email (fase iniziale).
# Imposta su 'False' per la modalità SharePoint (successiva).
# Controllo tramite variabile d'ambiente su Render.
EMAIL_ONLY_MODE = os.environ.get("EMAIL_ONLY_MODE", "True").lower() == "true"

# Dettagli per la modalità solo email
INITIAL_RECIPIENT_EMAIL = os.environ.get("INITIAL_RECIPIENT_EMAIL", "destinatario.iniziale@alten.it")
INITIAL_EMAIL_SUBJECT = os.environ.get("INITIAL_EMAIL_SUBJECT", "Modulo Competenze Alten - Le mie risposte")

# --- CONFIGURAZIONE SHAREPOINT (per fase successiva e upload automatico opzionale) ---
# Credenziali e URL del tuo "altro SharePoint" (DA SOSTITUIRE CON VARIABILI D'AMBIENTE SU RENDER!)
# Queste sono solo PLACEHOLDER. Non usarle così in produzione.
# Devi consultare la documentazione API del tuo specifico sistema SharePoint.
GENERIC_SHAREPOINT_API_KEY = os.environ.get("GENERIC_SHAREPOINT_API_KEY", "YOUR_API_KEY")
GENERIC_SHAREPOINT_UPLOAD_API_URL = os.environ.get("GENERIC_SHAREPOINT_UPLOAD_API_URL", "https://your.genericsite.com/api/upload") 

# Questo è l'URL della cartella SharePoint che gli utenti dovrebbero vedere nel browser
# e dove dovrebbero caricare manualmente i loro file.
# DEVI SOSTITUIRE QUESTO URL CON IL LINK REALE ALLA TUA CARTELLA SHAREPOINT.
SHAREPOINT_FOLDER_BROWSER_URL = os.environ.get("SHAREPOINT_FOLDER_BROWSER_URL", "https://your.sharepoint.com/sites/YourSite/SharedDocuments/YourFolder")


def upload_file_to_generic_sharepoint(file_path, file_name):
    """
    Carica un file su un sistema di storage generico (il tuo "altro SharePoint").
    Questa funzione è un placeholder e DEVE ESSERE PERSONALIZZATA in base
    alla documentazione API del sistema specifico.
    """
    logging.info(f"Tentativo di upload di '{file_name}' a SharePoint generico.")

    headers = {
        "Authorization": f"Bearer {GENERIC_SHAREPOINT_API_KEY}", 
    }

    try:
        with open(file_path, 'rb') as f: 
            response = requests.put(GENERIC_SHAREPOINT_UPLOAD_API_URL + f"/{file_name}", headers=headers, data=f)
            response.raise_for_status() 

        logging.info(f"File '{file_name}' caricato su SharePoint generico con successo. Risposta: {response.status_code}")
        return True
    except FileNotFoundError:
        logging.error(f"Errore: File '{file_path}' non trovato per l'upload a SharePoint generico.")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Errore durante l'upload del file a SharePoint generico: {e}. Risposta: {getattr(e.response, 'text', 'Nessuna risposta testuale')}")
        return False


# Definisce la rotta principale dell'applicazione ("/")
@app.route("/", methods=["GET", "POST"])
def index():
    success_message = None
    show_delete_button = False
    user_id = None 
    user_filename = None
    nome_utente = "" # Inizializza per essere sicuro che sia sempre definito

    if request.method == "POST":
        user_id = get_next_id() 

        # Preleva i dati dal form
        nome = request.form.get("nome", "")
        nome_utente = nome # Salva il nome per usarlo nel filename
        email = request.form.get("email", "")
        istruzione = request.form.get("istruzione", "")
        studi = request.form.get("studi", "")
        certificati = request.form.get("certificati", "")
        sede = request.form.get("sede", "")
        esperienza = request.form.get("esperienza", "")
        esperienza_alten = request.form.get("esperienza_alten", "")
        clienti_railway = request.form.getlist("clienti")
        clienti_str = ", ".join(clienti_railway) if clienti_railway else ""
        area_railway = request.form.getlist("area_railway")
        area_str = ", ".join(area_railway) if area_railway else ""
        normative = request.form.get("normative", "")
        metodologia = request.form.getlist("metodologia")
        metodologia_str = ", ".join(metodologia) if metodologia else ""
        sistemi_operativi = request.form.get("SistemiOperativi", "")
        altro = request.form.get("altro", "") 
        hobby = request.form.get("hobby", "")


        # Elaborazione delle sezioni dinamiche dei "Progetti" 
        scelte_progetti_sviluppo = request.form.getlist('sviluppo')
        dettagli_sviluppo = {area: [] for area in ["Applicativi", "Firmware", "Web", "Mobile", "Scada", "Plc"]}
        for area in dettagli_sviluppo.keys():
            if area not in scelte_progetti_sviluppo: continue
            linguaggi = request.form.getlist(f'linguaggi_{area.lower()}[]')
            tool = request.form.getlist(f'tool_{area.lower()}[]')
            ambito = request.form.getlist(f'Ambito_{area.lower()}[]')
            durata = request.form.getlist(f'durata_{area.lower()}[]')
            descrizione = request.form.getlist(f'descrizione_{area.lower()}[]')
            esperienze = []
            max_len = max(len(linguaggi), len(tool), len(ambito), len(durata), len(descrizione))
            for i in range(max_len):
                l = linguaggi[i] if i < len(linguaggi) else ""
                t = tool[i] if i < len(tool) else ""
                a = ambito[i] if i < len(ambito) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                esperienze.append(f"{l} | {t} | {a} | {e} | {d}")
            dettagli_sviluppo[area] = esperienze

        scelte_progetti_vv = request.form.getlist('v&v')
        dettagli_vv = {area: [] for area in ["functional_testing", "test_and_commisioning", "unit", "analisi_statica", "analisi_dinamica", "automatic_test", "piani_schematici", "procedure", "cablaggi", "FAT", "SAT", "doc"]}
        for area in dettagli_vv.keys():
            if area not in scelte_progetti_vv: continue
            tecnologie = request.form.getlist(f'tecnologie_{area}[]')
            ambito = request.form.getlist(f'azienda_{area}[]')
            durata = request.form.getlist(f'durata_{area}[]')
            descrizione = request.form.getlist(f'descrizione_{area}[]')
            esperienze = []
            max_len = max(len(tecnologie), len(ambito), len(durata), len(descrizione))
            for i in range(max_len):
                t = tecnologie[i] if i < len(tecnologie) else ""
                a = ambito[i] if i < len(ambito) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                esperienze.append(f"{t} | {a} | {e} | {d}")
            dettagli_vv[area] = esperienze
        
        scelte_progetti_system = request.form.getlist('system')
        dettagli_system = {area: [] for area in ["requirement_management", "requirement_engineering", "system_engineering", "project_engineering"]}
        for area in dettagli_system.keys():
            if area not in scelte_progetti_system: continue
            tecnologie = request.form.getlist(f'tecnologie_{area}[]')
            ambito = request.form.getlist(f'azienda_{area}[]')
            durata = request.form.getlist(f'durata_{area}[]')
            descrizione = request.form.getlist(f'descrizione_{area}[]')
            esperienze = []
            max_len = max(len(tecnologie), len(ambito), len(durata), len(descrizione))
            for i in range(max_len):
                t = tecnologie[i] if i < len(tecnologie) else ""
                a = ambito[i] if i < len(ambito) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                esperienze.append(f"{t} | {a} | {e} | {d}")
            dettagli_system[area] = esperienze

        scelte_progetti_safety = request.form.getlist('safety')
        dettagli_safety = {area: [] for area in ["RAMS", "hazard_analysis", "verification_report", "fire_safety", "reg_402"]}
        for area in dettagli_safety.keys():
            if area not in scelte_progetti_safety: continue
            tecnologie = request.form.getlist(f'tecnologie_{area}[]')
            ambito = request.form.getlist(f'azienda_{area}[]')
            durata = request.form.getlist(f'durata_{area}[]')
            descrizione = request.form.getlist(f'descrizione_{area}[]')
            esperienze = []
            max_len = max(len(tecnologie), len(ambito), len(durata), len(descrizione))
            for i in range(max_len):
                t = tecnologie[i] if i < len(tecnologie) else ""
                a = ambito[i] if i < len(ambito) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                esperienze.append(f"{t} | {a} | {e} | {d}")
            dettagli_safety[area] = esperienze

        scelte_progetti_segnalamento = request.form.getlist('segnalamento')
        dettagli_seg = {area: [] for area in ["piani_schematici_segnalamento", "cfg_impianti", "layout_apparecchiature", "architettura_rete", "computo_metrico"]}
        for area in dettagli_seg.keys():
            if area not in scelte_progetti_segnalamento: continue
            tecnologie = request.form.getlist(f'tecnologie_{area}[]')
            ambito = request.form.getlist(f'azienda_{area}[]')
            durata = request.form.getlist(f'durata_{area}[]')
            descrizione = request.form.getlist(f'descrizione_{area}[]')
            esperienze = []
            max_len = max(len(tecnologie), len(ambito), len(durata), len(descrizione))
            for i in range(max_len):
                t = tecnologie[i] if i < len(tecnologie) else ""
                a = ambito[i] if i < len(ambito) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                esperienze.append(f"{t} | {a} | {e} | {d}")
            dettagli_seg[area] = esperienze

        scelte_progetti_bim = request.form.getlist('bim')
        dettagli_bim = {area: [] for area in ["modellazione_e_digitalizzazione", "verifica_analisi_e_controllo_qualita", "gestione_coordinamento_e_simulazione", "visualizzazione_realtavirtuale_e_rendering"]}
        for area in dettagli_bim.keys():
            if area not in scelte_progetti_bim: continue
            tool = request.form.getlist(f'tool_{area}[]')
            azienda = request.form.getlist(f'azienda_{area}[]')
            durata = request.form.getlist(f'durata_{area}[]')
            descrizione = request.form.getlist(f'descrizione_{area}[]')
            certificazione = request.form.getlist(f'certificazioni_{area}[]')
            esperienze = []
            max_len = max(len(certificazione), len(tool), len(azienda), len(descrizione), len(durata))
            for i in range(max_len):
                t = tool[i] if i < len(tool) else ""
                a = azienda[i] if i < len(azienda) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                c = certificazione[i] if i < len(certificazione) else ""
                esperienze.append(f"{t} | {a} | {e} | {d} | {c}")
            dettagli_bim[area] = esperienze

        scelte_progetti_pm = request.form.getlist('pm')
        dettagli_pm = {area: [] for area in ["project_manager_office", "project_manager", "risk_manager", "resource_manager", "quality_manager", "communication_manager", "portfolio_manager", "program_manager","team_leader", "business_analyst", "contract_back_office"]}
        for area in dettagli_pm.keys():
            if area not in scelte_progetti_pm: continue
            tool = request.form.getlist(f'tool_{area}[]')
            azienda = request.form.getlist(f'azienda_{area}[]')
            durata = request.form.getlist(f'durata_{area}[]')
            descrizione = request.form.getlist(f'descrizione_{area}[]')
            esperienze = []
            max_len = max(len(tool), len(azienda), len(durata), len(descrizione))
            for i in range(max_len):
                t = tool[i] if i < len(tool) else ""
                a = azienda[i] if i < len(ambito) else ""
                e = durata[i] if i < len(durata) else ""
                d = descrizione[i] if i < len(descrizione) else ""
                esperienze.append(f"{t} | {a} | {e} | {d}")
            dettagli_pm[area] = esperienze

        # Crea un dizionario 'data' con tutte le informazioni raccolte dal form
        data = {
            "ID": user_id,
            "Nome": nome,
            "Email": email,
            "Istruzione": istruzione,
            "Indirizzo di studio": studi,
            "Sede Alten": sede,
            "Esperienza (anni)": esperienza,
            "Esperienza Alten (anni)": esperienza_alten,
            "Certificazioni": certificati,
            "Clienti Railway": clienti_str,
            "Area Railway": area_str,
            "Normative": normative,
            "Metodologie lavoro": metodologia_str,
            "Sistemi Operativi": sistemi_operativi,
            "Info aggiuntive": altro,
            "Hobby": hobby,
        }

        # Aggiunta delle varie sezioni di progetto con i dettagli in ordine al dizionario
        aggiungi_sezione("Sviluppo", scelte_progetti_sviluppo, dettagli_sviluppo, data)
        aggiungi_sezione("V&V", scelte_progetti_vv, dettagli_vv, data)
        aggiungi_sezione("Safety", scelte_progetti_safety, dettagli_safety, data)
        aggiungi_sezione("System", scelte_progetti_system, dettagli_system, data)
        aggiungi_sezione("Segnalamento", scelte_progetti_segnalamento, dettagli_seg, data)
        aggiungi_sezione("BIM", scelte_progetti_bim, dettagli_bim, data)
        aggiungi_sezione("Project Management", scelte_progetti_pm, dettagli_pm, data)

        # Controlla se l'azione del form è "submit_main" (pulsante "Invia")
        if request.form['action'] == 'submit_main':
            try:
                # La parte che scriveva sul file Excel principale è stata commentata
                # with excel_lock:
                #     logging.info(f"Lock acquisito per la scrittura del file Excel principale.")
                #     df = pd.read_excel(EXCEL_FILE)
                #     for col in data.keys():
                #         if col not in df.columns:
                #             df[col] = ''
                #     df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
                #     df.to_excel(EXCEL_FILE, index=False)
                #     logging.info(f"Dati scritti sul file Excel principale. {len(df)} righe totali. Lock rilasciato.")
                
                success_message = "Risposte inviate con successo!"

                # Generazione del nome del file con nome utente e data
                # Normalizza il nome utente per il filename (rimuovi spazi, caratteri speciali)
                sanitized_nome = "".join(c for c in nome_utente if c.isalnum() or c == '_').strip().replace(' ', '_')
                if not sanitized_nome: # Se il nome è vuoto o solo caratteri speciali
                    sanitized_nome = "Utente" # Nome di fallback
                
                user_filename = f"{sanitized_nome}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                logging.info(f"Nome del file utente generato: {user_filename}")
                user_filepath = os.path.join(USER_FILES_DIR, user_filename)
                logging.info(f"Percorso del file utente: {user_filepath}")
                user_df_single = pd.DataFrame([data])
                # Non includiamo l'ID nel file scaricato dall'utente, ma solo nel file principale se lo avessimo usato
                if 'ID' in user_df_single.columns:
                    user_df_single = user_df_single.drop(columns=["ID"])
                user_df_single.to_excel(user_filepath, index=False)
                
            except Exception as e:
                success_message = f'Si è verificato un errore durante l\'invio delle risposte: {e}'
                logging.error(f"Errore durante l'invio delle risposte o il salvataggio del file: {e}", exc_info=True)

        # Gestisce l'azione di esportazione al "SharePoint" generico (OPZIONALE)
        elif request.form['action'] == 'export_to_generic_sharepoint':
            filename_to_export = request.form.get("user_filename_to_export")

            if filename_to_export:
                file_path_to_export = os.path.join(USER_FILES_DIR, filename_to_export)
                if os.path.exists(file_path_to_export):
                    logging.info(f"Tentativo di esportare '{filename_to_export}' a SharePoint generico.")
                    if upload_file_to_generic_sharepoint(file_path_to_export, filename_to_export):
                        success_message = f"File '{filename_to_export}' esportato su SharePoint generico con successo!"
                        logging.info(f"File '{filename_to_export}' caricato su SharePoint generico.")
                    else:
                        success_message = f"Errore nell'esportazione di '{filename_to_export}' a SharePoint generico."
                        logging.error(f"Fallito l'upload di '{filename_to_export}' a SharePoint generico.")
                else:
                    success_message = f"File '{filename_to_export}' non trovato per l'esportazione."
                    logging.warning(f"File '{filename_to_export}' non trovato per l'esportazione a SharePoint generico.")
            else:
                success_message = "Nome file per l'esportazione su SharePoint generico non specificato."
                logging.warning("Nessun nome file fornito per l'esportazione su SharePoint generico.")
            
            user_filename = filename_to_export 


    # Passa tutte le variabili necessarie al template
    return render_template(
        "form.html", 
        success_message=success_message, 
        show_delete_button=show_delete_button, 
        user_filename=user_filename,
        sharepoint_folder_browser_url=SHAREPOINT_FOLDER_BROWSER_URL,
        email_only_mode=EMAIL_ONLY_MODE, 
        initial_recipient_email=INITIAL_RECIPIENT_EMAIL, 
        initial_email_subject=INITIAL_EMAIL_SUBJECT
    )

@app.route("/download")
def download():
    file_type = request.args.get("file", "main")

    if file_type == "personal":
        filename = request.args.get("filename")
        if not filename:
            abort(400, description="Missing filename parameter")
        
        user_filepath = os.path.join(USER_FILES_DIR, filename)
        if not os.path.exists(user_filepath):
            abort(404, description="File not found")

        return send_file(user_filepath, as_attachment=True, download_name=filename)
    
    # La parte per scaricare il file principale non è più rilevante se non viene salvato
    # elif file_type == "main": 
    #     try:
    #         with excel_lock:
    #             if not os.path.exists(EXCEL_FILE):
    #                 abort(404, description="File not found")
    #             return send_file(EXCEL_FILE, as_attachment=True, download_name="skills_trial.xlsx")
    #     except Exception as e:
    #         logging.error(f'Si è verificato un errore durante il download del file principale: {e}', exc_info=True)
    #         return redirect(url_for('index'))
    return abort(404, description="Invalid file type or file not found.") # Gestisce il caso di download di tipo "main" non più supportato

if __name__ == "__main__":
    app.run(debug=True)
