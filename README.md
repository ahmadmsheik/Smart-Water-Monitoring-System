# Smart Water Monitoring System

A final-year project for measuring water flow across multiple pipes and monitoring usage from a mobile app. The system combines flow-sensor hardware, a web API, analytics, push notifications, and a document-grounded chatbot.

## Components

- `sketch_apr5a/`: Arduino flow-sensor sketch. It measures flow pulses and sends readings over serial.
- `sketch_apr5b/`: ESP8266 sketch. It forwards sensor readings to the backend over Wi-Fi.
- `arduino_circuit/`: KiCad schematic and board files.
- `server/`: Flask API and SQLite-backed processing for flow readings, live streams, forecasts, consistency checks, anomalies, and notifications.
- `mobile app/water_monitoring_system_mobile/`: Flutter client with dashboard, charts, forecasts, anomalies, and chatbot screens.
- `chatbot_api/`: Flask question-answering API using retrieval-augmented generation, ChromaDB, sentence-transformer embeddings, and Ollama.

All components are included directly in this repository.

## Local configuration

- **ESP8266 firmware:** Copy `sketch_apr5b/secrets.example.h` to `sketch_apr5b/secrets.h`, then set the Wi-Fi name, password, and backend URL. `secrets.h` is ignored by Git.
- **Flutter app:** Copy `mobile app/water_monitoring_system_mobile/dart_defines.example.json` to `dart_defines.json`, set the backend and chatbot URLs, then run Flutter with `--dart-define-from-file=dart_defines.json`.
- **Chatbot documents:** Add documents you have permission to use under `chatbot_api/data/` and run the embedding setup. The local vector database is generated and ignored.

The Arduino sketch uses a C++ header because it cannot read `.env` files directly. The Flutter app reads compile-time configuration from Dart defines.
