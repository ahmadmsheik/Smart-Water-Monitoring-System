import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';

class ForecastScreen extends StatelessWidget {
  const ForecastScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder(
        future: ApiService.fetch("forecast"),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.hasError) {
            return const Center(child: Text("Failed to load data"));
          }

          final data = snapshot.data!;
          if (data.containsKey('message')) {
            return Center(
              child: Text(
                data['message'],
                style: const TextStyle(fontSize: 18, color: Colors.red),
              ),
            );
          }

          final forecast = data['forecast'] as Map<String, dynamic>;
          final entries = forecast.entries.toList();

          if (entries.isEmpty) {
            return const Center(child: Text("No forecast data available."));
          }

          final List<FlSpot> spots = [];
          double x = 0;
          for (final entry in entries) {
            final y = double.tryParse(entry.value.toString()) ?? 0.0;
            spots.add(FlSpot(x, y));
            x += 1;
          }

          final maxY = spots.map((e) => e.y).fold<double>(0.0, (a, b) => a > b ? a : b);

          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                const Text(
                  "3-Day Forecast",
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  height: 300,
                  child: LineChart(
                    LineChartData(
                      minY: 0,
                      maxY: maxY + 5,
                      titlesData: FlTitlesData(
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            getTitlesWidget: (value, meta) {
                              final index = value.toInt();
                              if (index < 0 || index >= entries.length) {
                                return const SizedBox.shrink();
                              }

                              final date = entries[index].key;
                              return Text(
                                date.substring(5), // e.g. "06-24"
                                style: const TextStyle(fontSize: 10),
                              );
                            },
                          ),
                        ),
                        leftTitles: AxisTitles(
                          axisNameWidget: const Text(
                            "Usage (Liters)",
                            style: TextStyle(fontSize: 12),
                          ),
                          axisNameSize: 32,
                          sideTitles: SideTitles(
                            showTitles: true,
                            getTitlesWidget: (value, meta) {
                              return Text(
                                "${value.toStringAsFixed(0)} L",
                                style: const TextStyle(fontSize: 10),
                              );
                            },
                          ),
                        ),
                      ),
                      gridData: const FlGridData(show: true),
                      borderData: FlBorderData(show: true),
                      lineBarsData: [
                        LineChartBarData(
                          spots: spots,
                          isCurved: true,
                          color: Colors.blue,
                          barWidth: 3,
                          belowBarData: BarAreaData(
                            show: true,
                            color: Colors.blue.withOpacity(0.3),
                          ),
                          dotData: const FlDotData(show: true),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
