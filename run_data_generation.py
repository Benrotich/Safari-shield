#!/usr/bin/env python3
"""
Run script for Safari-Shield data generation.
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))


from src.data.synthetic_generator import MPesaDataGenerator, generate_sample_data


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic M-Pesa transaction data'
    )
    parser.add_argument(
        '--customers',
        type=int,
        default=10000,
        help='Number of customers (default: 10000)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days to generate (default: 90)'
    )
    parser.add_argument(
        '--fraud-rate',
        type=float,
        default=0.03,
        help='Fraud rate (default: 0.03)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/synthetic/mpesa_transactions.csv',
        help='Output file path (default: data/synthetic/mpesa_transactions.csv)'
    )
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Generate small sample for testing'
    )

    args = parser.parse_args()

    if args.sample:
        print("Generating sample dataset...")
        df = generate_sample_data(
            output_path=args.output,
            n_customers=min(args.customers, 1000),
            days=min(args.days, 30),
            fraud_percentage=args.fraud_rate
        )
    else:
        print(
            f"Generating dataset with {args.customers:,} customers for {args.days} days..."
        )
        generator = MPesaDataGenerator(n_customers=args.customers)
        df = generator.generate_dataset(
            days=args.days,
            fraud_percentage=args.fraud_rate,
            save_to_file=True
        )

    print("\nDataset generated successfully!")
    print(f"Shape: {df.shape}")
    print(f"Fraud rate: {df['is_fraud'].mean():.2%}")
    print(f"Saved to: {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
