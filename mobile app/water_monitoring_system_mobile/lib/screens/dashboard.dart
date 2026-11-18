import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/stream_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final StreamService _streamService1 = StreamService();
  final StreamService _streamService2 = StreamService();
  final StreamService _streamService3 = StreamService();

  late Stream<double> _flowRateStream1;
  late Stream<double> _flowRateStream2;
  late Stream<double> _flowRateStream3;

  @override
  void initState() {
    super.initState();
    _flowRateStream1 = _streamService1.streamFlowRate(1); // main
    _flowRateStream2 = _streamService2.streamFlowRate(2); // branch 1
    _flowRateStream3 = _streamService3.streamFlowRate(3); // branch 2
  }

  @override
  void dispose() {
    _streamService1.dispose();
    _streamService2.dispose();
    _streamService3.dispose();
    super.dispose();
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
            return const Center(child: Text("Failed to load data"));
          }

          final data = snapshot.data as Map<String, dynamic>;
          final List<Color> cardColors = [
            Colors.blue.shade100,
            Colors.green.shade100,
            Colors.purple.shade100,
            Colors.orange.shade100,
          ];

          final List<Map<String, String>> cards = [
            {
              'title': 'Today\'s Usage',
              'value': '${data['today_usage']} L',
            },
            {
              'title': 'This Week Usage',
              'value': '${data['this_week_usage']} L',
            },
            {
              'title': 'This Month Usage',
              'value': '${data['this_month_usage']} L',
            },
            {
              'title': 'Last Month Usage',
              'value': '${data['last_month_usage']} L',
            },
          ];

          return ListView(
            padding: const EdgeInsets.all(12),
            children: [
              // Real-time flow rate card
              Column(
                children: [
                  buildFlowRateCard(_flowRateStream1, "Main Inlet Flow Rate"),
                  const SizedBox(height: 12),
                  buildFlowRateCard(_flowRateStream2, "Branch 1 Flow Rate"),
                  const SizedBox(height: 12),
                  buildFlowRateCard(_flowRateStream3, "Branch 2 Flow Rate"),
                ],
              ),

              const SizedBox(height: 16),

              // Usage cards
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: cards.asMap().entries.map((entry) {
                  final i = entry.key;
                  final card = entry.value;

                  return SizedBox(
                    width: (MediaQuery.of(context).size.width - 36) / 2,
                    child: Card(
                      color: cardColors[i % cardColors.length],
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              card['title']!,
                              textAlign: TextAlign.center,
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              card['value']!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(fontSize: 18),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget buildFlowRateCard(Stream<double> stream, String title) {
    return Card(
      child: StreamBuilder<double>(
        stream: stream,
        builder: (context, snapshot) {
          print(
              '[UI] $title -> hasData=${snapshot.hasData}, value=${snapshot.data}');
          return Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                Text(
                  title,
                  style: const TextStyle(
                      fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.water_drop,
                        size: 24, color: Theme.of(context).primaryColor),
                    const SizedBox(width: 8),
                    Text(
                      snapshot.connectionState == ConnectionState.active ||
                              snapshot.hasData
                          ? '${snapshot.data?.toStringAsFixed(2) ?? "0.00"} L/min'
                          : 'Loading...',
                      style: const TextStyle(
                          fontSize: 24, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
