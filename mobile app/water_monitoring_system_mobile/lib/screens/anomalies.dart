import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AnomaliesScreen extends StatelessWidget {
  const AnomaliesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Anomaly Detection")),
      body: FutureBuilder(
        future: ApiService.fetch("latest-anomalies"),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (!snapshot.hasData || snapshot.hasError) {
            return const Center(child: Text("Failed to load data"));
          }

          final data = snapshot.data as Map<String, dynamic>;
          print('DEBUG: Received data: $data');

          if (data.containsKey('message')) {
            return Center(child: Text(data['message']));
          }

          // Extract the anomalies list
          final anomaliesList = data['anomalies'] as List<dynamic>? ?? [];

          if (anomaliesList.isEmpty) {
            return const Center(
              child: Text('No anomalies detected', style: TextStyle(fontSize: 18)),
            );
          }

          // Display all anomalies
          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: anomaliesList.length,
            itemBuilder: (context, index) {
              final anomaly = anomaliesList[index] as Map<String, dynamic>;

              final massBalance = anomaly['mass_balance'] as Map<String, dynamic>? ?? {};
              final tapStuckOn = anomaly['tap_stuck_on'] as List<dynamic>? ?? [];
              final inactivePipes = anomaly['inactive_pipe'] as List<dynamic>? ?? [];

              // Skip anomaly if all sections empty
              if (massBalance.isEmpty && tapStuckOn.isEmpty && inactivePipes.isEmpty) {
                return const SizedBox.shrink();
              }

              return Card(
                margin: const EdgeInsets.symmetric(vertical: 8),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Saved at: ${anomaly["saved_at"] ?? "Unknown"}',
                          style: const TextStyle(fontWeight: FontWeight.bold)),

                      if (massBalance.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        const Text('💧 Mass Balance Anomaly',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                        ...massBalance.entries.map((entry) {
                          final timestamp = entry.key;
                          final vals = entry.value as Map<String, dynamic>;
                          return ListTile(
                            title: Text('📅 Time: $timestamp'),
                            subtitle: Text(
                              'Sensor 1: ${vals["1"]}\n'
                              'Sensor 2: ${vals["2"]}\n'
                              'Sensor 3: ${vals["3"]}\n'
                              'Residual: ${vals["residual"]}',
                            ),
                          );
                        }),
                      ],

                      if (tapStuckOn.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        const Text('🚰 Tap Stuck Events',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                        ...tapStuckOn.map((event) {
                          return ListTile(
                            title: Text('Sensor: ${event["sensor"]}'),
                            subtitle: Text(
                              'Start: ${event["start"]}\n'
                              'End: ${event["end"]}\n'
                              'Duration: ${event["duration_seconds"] ?? "N/A"} sec',
                            ),
                          );
                        }),
                      ],

                      if (inactivePipes.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        const Text('🚫 Inactive Pipe(s)',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                        ...inactivePipes.map((pipe) {
                          return ListTile(
                            title: Text('Sensor ${pipe["sensor"]} had no flow'),
                            subtitle: Text(
                              'Start: ${pipe["start"]}\n'
                              'End: ${pipe["end"]}\n'
                              'Reason: ${pipe["reason"]}',
                            ),
                          );
                        }),
                      ],
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
