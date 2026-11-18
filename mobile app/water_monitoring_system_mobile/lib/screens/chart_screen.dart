import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';

class ChartsScreen extends StatelessWidget {
  const ChartsScreen({super.key});

  Widget buildLineChart(Map<String, dynamic> plotData, String title, String unit) {
    final labels = plotData.keys.toList();
    final spots = plotData.entries
        .toList()
        .asMap()
        .entries
        .map((entry) => FlSpot(
              entry.key.toDouble(),
              double.tryParse(entry.value.value.toString()) ?? 0.0,
            ))
        .toList();

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 12),
            SizedBox(
              height: 220,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: true),
                  titlesData: FlTitlesData(
                    leftTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: true),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: 1,
                        getTitlesWidget: (value, meta) {
                          final idx = value.toInt();
                          if (idx < 0 || idx >= labels.length) {
                            return const SizedBox.shrink();
                          }
                          return Text(
                            labels[idx],
                            style: const TextStyle(fontSize: 10),
                          );
                        },
                      ),
                    ),
                    topTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: true),
                  minX: 0,
                  maxX: (labels.length - 1).toDouble(),
                  minY: 0,
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: Colors.blue,
                      barWidth: 3,
                      dotData: const FlDotData(show: false),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text('Unit: $unit',
                style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder(
        future: ApiService.fetch("analyze"), 
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.hasError) {
            return const Center(child: Text("Failed to load chart data."));
          }

          final data = snapshot.data as Map<String, dynamic>;

          final hourlyData =
              data['average_hourly_flow_rate'] as Map<String, dynamic>;
          final dailyData =
              data['daily_plot_data'] as Map<String, dynamic>;
          final monthlyData =
              data['monthly_plot_data'] as Map<String, dynamic>;

          return SingleChildScrollView(
            child: Column(
              children: [
                buildLineChart(hourlyData, "Average Hourly Flow Rate", "L/min"),
                buildLineChart(dailyData, "Daily Usage", "L"),
                buildLineChart(monthlyData, "Monthly Usage", "L"),
              ],
            ),
          );
        },
      ),
    );
  }
}
