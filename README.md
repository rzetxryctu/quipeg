# Quipeg v3 — Simulatore di Rete Quantistica Interplanetaria

[![PyPI version](https://img.shields.io/pypi/v/quipeg)](https://pypi.org/project/quipeg/)
[![Python](https://img.shields.io/pypi/pyversions/quipeg)](https://pypi.org/project/quipeg/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue)](LICENSE)
[![Downloads](https://static.pepy.tech/badge/quipeg)](https://pepy.tech/project/quipeg)

## Cos'è Quipeg?

**Quipeg** (Quantum Internet Protocol & Entanglement Gateway) è uno strumento gratuito e open-source che **simula come funzionerebbe una rete qubitistica su scala globale** — tipo un internet del futuro, ma basato sulla fisica quantistica invece che sui classici cavi di fibra ottica.

### In parole povere

Immagina di voler creare una rete di comunicazione **inviolabile** che collega città di tutto il mondo usando le proprietà della fisica quantistica:

- **Nodi**: città o stazioni (es. Londra, Roma, Tokyo, New York)
- **Link**: collegamenti in fibra ottica tra le città
- **Entanglement**: "teletrasporto quantistico" che trasmette informazioni in modo sicuro che nessun hacker può intercettare
- **Ripetitori quantistici**: stazione che estendono la portata della rete

**Quipeg** permette di **disegnare la rete, simulare il decadimento dei segnali, ottimizzare il routing, e calocare quali connessioni sono abbastanza buone** per la crittografia quantistica.

## A cosa serve concretamente?

- 🔬 **Ricerca**: simula reti QKD (Quantum Key Distribution) per articoli scientifici e tesi
- 🎓 **Didattica**: impara come funzionano i ripetitori quantistici e la purificazione dell'entanglement
- 🛠️ **Prototipazione**: testa topologie di reti quantistiche prima di costruirle davvero
- 📊 **Analisi**: visualizza mappe interattive conmetriche di ogni collegamento (fidelity, QBER, key rate)

## Versione 3.0 — cosa c'è di nuovo?

| Funzionalità | Descrizione semplice |
|---|---|
| **Modello di swap corretto** | Il calcolo della fedeltà dopo lo scambio d'entanglement ora usa la formula quantistica corretta (non più un semplice media aritmetica) |
| **Purificazione DEJMPS** | Implementa un protocollo che "pulisce" le conexioni rumorose, migliorandone la qualità |
| **Decoerenza T1/T2** | Simula in modo realistico perde le memorie quantistiche nel tempo, distinguendo due tipi diversi di rumore |
| **Mappa HTML interattiva** | Genera una mappa SVG standalone che funziona offline, con tooltip che mostrano le metriche di ogni link |
| **Esportatore GeoJSON** | Esporta la reto in formato per mappe geografiche |
| **CLI completa** | Comandi `quipeg render`, `quipeg export`, `quipeg simulate` direttamente dal terminale |
| **~140 test** | Suite di test comprensiva |

## Installazione

```bash
# Con PyPI (quando pubblicato)
pip install quipeg

# Oppure da sorgente
pip install -e .
```

**Requisiti**: Python 3.9+ — **zero dipendenze esterne**.

## Esempio rapido

```python
from quipeg import QuantumNetwork

# Crea una rete globale demo con 8 nodi
net = QuantumNetwork.demo()

# Simula Londra → Tokyo
results = net.end_to_end("London", "Tokyo")
print(f"Fidelity: {results['fidelity']:.4f}")
print(f"QBER: {results['qber']:.5f}")

# Genera una mappa interattiva HTML
net.render("mappa.html")
```

## Modello di fisica

### Distribuzione di Entanglement

Le coppie di fotoni sono distribuite via fibra ottica. La fedeltà F evolve con due canali di decoerenza indipendenti:

| Canale | Costante | Effetto |
|---|---|---|
| Rilassamento T1 | µs–ms | Decadimento verso 0.5 |
| Dephasing T2 | µs–ms | Decadimento verso 0.25 (completamente misto) |

### Scambio di Entanglement

Quando le coppie di Bell (F₁, F₂) vengono scambiate tramite misura di Bell:

```
F_swap = F₁ · F₂ + (1-F₁)(1-F₂) / 3
```

### QBER e Secret Key Rate (BB84)

```
QBER = (1 - F) / 2
SKR = ½ · η · μ · p_repeat · (1 - 2·QBER - H₂(QBER)) · f_EC · R
```

## Struttura del Repository

```
src/quipeg/       # Codice sorgente principale
tests/            # Suite di test (~140 test)
CHANGELOG.md      # Cronologia delle versioni
LICENSE           # Apache 2.0
README.md         # Questa documentazione
```

## Licenza

Apache License 2.0 — open source, usabile liberamente anche per progetti commerciali.
