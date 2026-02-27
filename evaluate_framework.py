#!/usr/bin/env python3
"""
Minimal Model Evaluation Framework Demo
Shows metrics without running actual Grok models
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from evaluation.benchmark_data import MEDICAL_QUERIES, LEGAL_QUERIES, ALL_QUERIES
from evaluation.metrics import MetricsCalculator
import json

def generate_mock_results():
    """Generate mock evaluation results for demonstration"""
    
    # Simulate results for 3 Grok models
    models = ['grok-beta', 'grok-2-latest', 'grok-2-vision-1212']
    
    results = {}
    metrics_calc = MetricsCalculator()
    
    for model in models:
        # Mock performance (grok-2-vision-1212 > grok-2-latest > grok-beta)
        if model == 'grok-beta':
            base_accuracy = 0.70
            base_latency = 1.2
            base_cost = 0.0005
        elif model == 'grok-2-latest':
            base_accuracy = 0.80
            base_latency = 2.1
            base_cost = 0.002
        else:  # grok-2-vision-1212
            base_accuracy = 0.88
            base_latency = 3.5
            base_cost = 0.024
        
        # Generate per-query results
        query_results = []
        for i, query in enumerate(ALL_QUERIES):
            # Vary accuracy by query type
            type_modifier = {
                'factual': 0.05,
                'reasoning': -0.05,
                'long_context': -0.10,
                'edge_case': -0.15,
                'ambiguous': -0.08,
                'creative': 0.02
            }.get(query['type'], 0)
            
            accuracy = min(1.0, max(0.0, base_accuracy + type_modifier))
            
            query_results.append({
                'query': query['query'],
                'type': query['type'],
                'domain': query['domain'],
                'accuracy': accuracy,
                'latency': base_latency * (0.8 + i * 0.02),  # Vary latency
                'retrieved_docs': 5,
                'relevant_docs': int(5 * accuracy),
                'tokens_used': 150 + i * 10
            })
        
        # Calculate aggregate metrics
        accuracies = [r['accuracy'] for r in query_results]
        latencies = [r['latency'] for r in query_results]
        
        # Simple MRR and NDCG calculation
        mrr = sum(1.0 / (i + 1) for i, r in enumerate(query_results) if r['relevant_docs'] > 0) / len(query_results)
        ndcg = sum(r['relevant_docs'] / (i + 1) for i, r in enumerate(query_results)) / len(query_results)
        
        results[model] = {
            'query_results': query_results,
            'metrics': {
                'avg_accuracy': sum(accuracies) / len(accuracies),
                'min_accuracy': min(accuracies),
                'max_accuracy': max(accuracies),
                'mrr': mrr,
                'ndcg@5': ndcg / 5.0,  # Normalize
                'avg_latency': sum(latencies) / len(latencies),
                'p50_latency': sorted(latencies)[len(latencies)//2],
                'p95_latency': sorted(latencies)[int(len(latencies)*0.95)],
                'p99_latency': sorted(latencies)[int(len(latencies)*0.99)],
                'total_tokens': sum(r['tokens_used'] for r in query_results),
                'total_cost': sum(r['tokens_used'] for r in query_results) * base_cost / 1000
            }
        }
    
    return results

def print_evaluation_report(results):
    """Print comprehensive evaluation report"""
    
    print("=" * 80)
    print("🔬 MODEL EVALUATION FRAMEWORK - COMPREHENSIVE REPORT")
    print("=" * 80)
    
    # Test Set Summary
    print("\n📊 TEST SET SUMMARY")
    print("-" * 80)
    print(f"Total Queries: {len(ALL_QUERIES)}")
    print(f"Medical Queries: {len(MEDICAL_QUERIES)}")
    print(f"Legal Queries: {len(LEGAL_QUERIES)}")
    print("\nQuery Types:")
    type_counts = {}
    for q in ALL_QUERIES:
        type_counts[q['type']] = type_counts.get(q['type'], 0) + 1
    for qtype, count in sorted(type_counts.items()):
        print(f"  • {qtype.replace('_', ' ').title()}: {count}")
    
    # Model Comparison
    print("\n" + "=" * 80)
    print("📈 MODEL COMPARISON")
    print("=" * 80)
    
    for model, data in results.items():
        metrics = data['metrics']
        print(f"\n🤖 {model}")
        print("-" * 80)
        print(f"  Accuracy:       {metrics['avg_accuracy']:.1%} (min: {metrics['min_accuracy']:.1%}, max: {metrics['max_accuracy']:.1%})")
        print(f"  MRR:            {metrics['mrr']:.3f}")
        print(f"  NDCG@5:         {metrics['ndcg@5']:.3f}")
        print(f"  Avg Latency:    {metrics['avg_latency']:.2f}s")
        print(f"  P50 Latency:    {metrics['p50_latency']:.2f}s")
        print(f"  P95 Latency:    {metrics['p95_latency']:.2f}s")
        print(f"  P99 Latency:    {metrics['p99_latency']:.2f}s")
        print(f"  Total Tokens:   {metrics['total_tokens']:,}")
        print(f"  Total Cost:     ${metrics['total_cost']:.4f}")
    
    # Per-Domain Performance
    print("\n" + "=" * 80)
    print("📋 PER-DOMAIN PERFORMANCE")
    print("=" * 80)
    
    for model, data in results.items():
        print(f"\n🤖 {model}")
        print("-" * 80)
        
        # Group by domain
        domain_results = {}
        for qr in data['query_results']:
            domain = qr['domain']
            if domain not in domain_results:
                domain_results[domain] = []
            domain_results[domain].append(qr)
        
        for domain, qrs in sorted(domain_results.items()):
            avg_acc = sum(r['accuracy'] for r in qrs) / len(qrs)
            avg_lat = sum(r['latency'] for r in qrs) / len(qrs)
            print(f"  {domain.title():12} Accuracy: {avg_acc:.1%}  |  Latency: {avg_lat:.2f}s  |  Queries: {len(qrs)}")
    
    # Per-Type Performance
    print("\n" + "=" * 80)
    print("📊 PER-TYPE PERFORMANCE")
    print("=" * 80)
    
    for model, data in results.items():
        print(f"\n🤖 {model}")
        print("-" * 80)
        
        # Group by type
        type_results = {}
        for qr in data['query_results']:
            qtype = qr['type']
            if qtype not in type_results:
                type_results[qtype] = []
            type_results[qtype].append(qr)
        
        for qtype, qrs in sorted(type_results.items()):
            avg_acc = sum(r['accuracy'] for r in qrs) / len(qrs)
            avg_lat = sum(r['latency'] for r in qrs) / len(qrs)
            type_label = qtype.replace('_', ' ').title()
            print(f"  {type_label:15} Accuracy: {avg_acc:.1%}  |  Latency: {avg_lat:.2f}s  |  Queries: {len(qrs)}")
    
    # Winners
    print("\n" + "=" * 80)
    print("🏆 WINNERS")
    print("=" * 80)
    
    best_accuracy = max(results.items(), key=lambda x: x[1]['metrics']['avg_accuracy'])
    best_latency = min(results.items(), key=lambda x: x[1]['metrics']['avg_latency'])
    best_mrr = max(results.items(), key=lambda x: x[1]['metrics']['mrr'])
    best_cost = min(results.items(), key=lambda x: x[1]['metrics']['total_cost'])
    
    print(f"  Best Accuracy:  {best_accuracy[0]} ({best_accuracy[1]['metrics']['avg_accuracy']:.1%})")
    print(f"  Best Latency:   {best_latency[0]} ({best_latency[1]['metrics']['avg_latency']:.2f}s)")
    print(f"  Best MRR:       {best_mrr[0]} ({best_mrr[1]['metrics']['mrr']:.3f})")
    print(f"  Best Cost:      {best_cost[0]} (${best_cost[1]['metrics']['total_cost']:.4f})")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("💡 DATA-DRIVEN RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n1. Model Selection:")
    print(f"   • Production: {best_accuracy[0]} (highest accuracy)")
    print(f"   • Development: {best_cost[0]} (lowest cost)")
    print(f"   • Real-time: {best_latency[0]} (lowest latency)")
    
    print("\n2. Query Type Optimization:")
    # Find worst performing type
    worst_type = None
    worst_acc = 1.0
    for model, data in results.items():
        type_results = {}
        for qr in data['query_results']:
            qtype = qr['type']
            if qtype not in type_results:
                type_results[qtype] = []
            type_results[qtype].append(qr)
        
        for qtype, qrs in type_results.items():
            avg_acc = sum(r['accuracy'] for r in qrs) / len(qrs)
            if avg_acc < worst_acc:
                worst_acc = avg_acc
                worst_type = qtype
    
    if worst_type:
        print(f"   • Focus on {worst_type.replace('_', ' ')} queries (lowest accuracy: {worst_acc:.1%})")
        print(f"   • Consider specialized prompts or retrieval strategies")
    
    print("\n3. Retrieval Configuration:")
    print("   • Current: top_k=5 documents")
    print("   • Recommendation: Increase to top_k=7 for complex queries")
    print("   • Enable adaptive retrieval based on query complexity")
    
    print("\n4. Cost Optimization:")
    total_cost = sum(r['metrics']['total_cost'] for r in results.values())
    print(f"   • Total evaluation cost: ${total_cost:.4f}")
    print(f"   • Use {best_cost[0]} for development (${best_cost[1]['metrics']['total_cost']:.4f})")
    print(f"   • Enable semantic caching (40% cost reduction)")
    
    print("\n" + "=" * 80)
    print("✅ EVALUATION COMPLETE")
    print("=" * 80)

def save_report(results):
    """Save detailed JSON report"""
    filename = "evaluation_report.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Detailed report saved to: {filename}")

if __name__ == '__main__':
    print("\n🚀 Starting Model Evaluation Framework Demo...\n")
    
    # Generate mock results
    results = generate_mock_results()
    
    # Print comprehensive report
    print_evaluation_report(results)
    
    # Save detailed report
    save_report(results)
    
    print("\n🎉 Demo complete! Framework demonstrates:")
    print("  ✓ Per-domain benchmarks (medical, legal)")
    print("  ✓ Balanced test sets (6 query types)")
    print("  ✓ Comprehensive metrics (accuracy, MRR, NDCG, latency, cost)")
    print("  ✓ Data-driven recommendations")
    print()
