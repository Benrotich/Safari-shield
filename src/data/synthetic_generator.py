"""Synthetic M-Pesa transaction data generator"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Optional
import hashlib
import json
from pathlib import Path

from src.data.schemas import (
    TransactionType,
    FraudType,
    Channel,
    CustomerProfile,
    FraudPattern
)


class MPesaDataGenerator:
    """Generate realistic M-Pesa transaction data with fraud patterns"""

    def __init__(
        self,
        n_customers: int = 10000,
        n_agents: int = 500,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        seed: int = 42
        
    ):
        self.n_customers = n_customers
        self.n_agents = n_agents
        self.start_date = start_date or datetime.now() - timedelta(days=90)
        self.end_date = end_date or datetime.now()
        self.seed = seed
        self.customer_last_tx_time = {} # Tracks {customer_id: datetime}

        # Set random seeds
        np.random.seed(seed)
        random.seed(seed)

        # Initialize data structures
        self.customer_profiles: Dict[str, CustomerProfile] = {}
        self.agent_ids: List[str] = []
        self.fraud_patterns: Dict[FraudType, FraudPattern] = {}

        # Generate base data
        self._generate_customer_profiles()
        self._generate_agent_ids()
        self._initialize_fraud_patterns()

        # Statistics tracking
        self.stats = {
            'total_transactions': 0,
            'fraudulent_transactions': 0,
            'total_amount': 0.0
        }

    def _generate_customer_profiles(self):
        print(f"Generating {self.n_customers} customer profiles...")
        for i in range(self.n_customers):
            cust_id = f"CUST{str(i).zfill(8)}"
            reg_date = self.start_date - timedelta(days=np.random.randint(365, 730))
            typical_hours = sorted(random.sample(range(24), random.randint(2, 5)))
            profile = CustomerProfile(
                customer_id=cust_id,
                registration_date=reg_date,
                typical_transaction_times=typical_hours,
                transaction_frequency_daily=np.random.exponential(0.5) + 0.1,
                avg_transaction_amount=np.random.lognormal(6, 1),
                device_fingerprint=f"DEV_{hashlib.md5(cust_id.encode()).hexdigest()[:8]}",
                risk_score=np.random.beta(2, 10)
            )
            self.customer_profiles[cust_id] = profile
        print(f"Generated {len(self.customer_profiles)} customer profiles.")

    def _generate_agent_ids(self):
        self.agent_ids = [f"AGENT{str(i).zfill(6)}" for i in range(self.n_agents)]

    def _initialize_fraud_patterns(self):
        # Use the Enum members directly as keys
        self.fraud_patterns[FraudType.SIM_SWAP] = FraudPattern(
            pattern_type=FraudType.SIM_SWAP,
            characteristics={
                "device_change": True,
                "sim_change": True,
                "unusual_time": True,
                "large_amount": True,
                "new_recipient": True,
                "rapid_transactions": True,
                "location_change": True
            },
            probability=0.001,
            severity="high"
        )
        self.fraud_patterns[FraudType.SOCIAL_ENGINEERING] = FraudPattern(
            pattern_type=FraudType.SOCIAL_ENGINEERING,
            characteristics={
                "urgent_language": True,
                "impersonation": True,
                "information_gathering": True,
                "medium_amount": True,
                "familiar_recipient": False
            },
            probability=0.002,
            severity="medium"
        )
        self.fraud_patterns[FraudType.AGENT_FRAUD] = FraudPattern(
            pattern_type=FraudType.AGENT_FRAUD,
            characteristics={
                "agent_involved": True,
                "round_amounts": True,
                "fake_reversals": True,
                "balance_tampering": True,
                "after_hours": True
            },
            probability=0.003,
            severity="high"
        )
        self.fraud_patterns[FraudType.ACCOUNT_TAKEOVER] = FraudPattern(
            pattern_type=FraudType.ACCOUNT_TAKEOVER,
            characteristics={
                "password_reset": True,
                "multiple_failed_logins": True,
                "profile_changes": True,
                "dormant_account": True,
                "unusual_activity": True
            },
            probability=0.0015,
            severity="high"
        )

    def _generate_normal_transaction(
        self,
        customer_id: str,
        timestamp: datetime,
        profile: CustomerProfile
    ) -> Dict[str, Any]:
        
        # 1. NEW: Calculate Velocity logic
        last_time = self.customer_last_tx_time.get(customer_id)
        if last_time:
            time_diff = (timestamp - last_time).total_seconds()
        else:
            time_diff = 86400.0  # Default to 1 day if first transaction
            
        is_high_velocity = time_diff < 30  # Threshold: 30 seconds
        
        # Update tracker for next time
        self.customer_last_tx_time[customer_id] = timestamp

        
        
        profile = self.customer_profiles[customer_id]

        tx_type_probs = {
            TransactionType.SEND_MONEY: 0.40,
            TransactionType.WITHDRAW_CASH: 0.25,
            TransactionType.BUY_GOODS: 0.15,
            TransactionType.PAY_BILL: 0.12,
            TransactionType.AIRTIME: 0.05,
            TransactionType.DEPOSIT: 0.02,
            TransactionType.LOAN_DISBURSEMENT: 0.01
        }

        tx_type = np.random.choice(list(tx_type_probs.keys()), p=list(tx_type_probs.values()))
        tx_type_str = tx_type.value if hasattr(tx_type, 'value') else str(tx_type)

        if tx_type == TransactionType.SEND_MONEY:
            base_amount = np.random.lognormal(np.log(profile.avg_transaction_amount), 0.5)
        elif tx_type == TransactionType.WITHDRAW_CASH:
            base_amount = np.random.lognormal(np.log(1000), 0.7)
        else:
            base_amount = np.random.lognormal(np.log(500), 0.5)

        amount = min(base_amount, 70000)

        sender_msisdn = f"2547{random.randint(10000000, 99999999)}"
        receiver_msisdn = f"2547{random.randint(10000000, 99999999)}"

        balance_before = np.random.uniform(amount * 2, 100000)
        balance_after = balance_before - amount

        agent_id = None
        if tx_type in [TransactionType.WITHDRAW_CASH, TransactionType.DEPOSIT]:
            agent_id = random.choice(self.agent_ids)

        locations = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika"]
        location = random.choice(locations)

        device_id = profile.device_fingerprint
        sim_serial = f"SIM{hashlib.md5(customer_id.encode()).hexdigest()[:10]}"

        channel = random.choice(list(Channel))
        channel_str = channel.value if hasattr(channel, 'value') else str(channel)

        return {
            'transaction_id': f"TX{hashlib.md5(str(timestamp).encode()).hexdigest()[:12]}",
            'timestamp': timestamp,
            'customer_id': customer_id,
            'transaction_type': tx_type_str,
            'amount': round(amount, 2),
            'sender_msisdn': sender_msisdn,
            'receiver_msisdn': receiver_msisdn,
            'sender_balance_before': round(balance_before, 2),
            'sender_balance_after': round(balance_after, 2),
            'agent_id': agent_id,
            'location': location,
            'device_id': device_id,
            'sim_serial': sim_serial,
            'channel': channel_str,
            'is_fraud': False,
            'fraud_type': None,
            'fraud_description': None,
            'time_since_last_tx_seconds': round(time_diff, 2),
            'is_high_velocity': is_high_velocity
        }

    def _generate_fraud_transaction(
        self,
        customer_id: str,
        timestamp: datetime,
        fraud_type: FraudType
    ) -> Dict[str, Any]:
        """Generate a fraudulent transaction. fraud_type must be a FraudType enum"""
        profile = self.customer_profiles[customer_id]

        if not isinstance(fraud_type, FraudType):
            raise ValueError(f"Expected FraudType enum, got {fraud_type}")

        self.fraud_patterns[fraud_type]
        tx_data = self._generate_normal_transaction(customer_id, timestamp, profile)
        tx_data['is_fraud'] = True
        tx_data['fraud_type'] = fraud_type.value

        if fraud_type == FraudType.SIM_SWAP:
            tx_data['device_id'] = f"NEW_DEV_{hashlib.md5(str(timestamp).encode()).hexdigest()[:8]}"
            tx_data['sim_serial'] = f"NEW_SIM_{random.randint(100000, 999999)}"
            tx_data['amount'] = round(np.random.uniform(20000, 150000), 2)
            tx_data['location'] = "UNKNOWN"
            tx_data['timestamp'] = timestamp.replace(hour=np.random.choice([2, 3, 4, 5]))
            tx_data['fraud_description'] = "SIM swap attack detected - new device and SIM"
        elif fraud_type == FraudType.SOCIAL_ENGINEERING:
            tx_data['amount'] = round(np.random.uniform(5000, 30000), 2)
            tx_data['receiver_msisdn'] = f"2547{random.randint(10000000, 99999999)}"
            tx_data['fraud_description'] = "Social engineering - impersonation attempt"
        elif fraud_type == FraudType.AGENT_FRAUD:
            tx_data['agent_id'] = random.choice(self.agent_ids)
            tx_data['amount'] = round(np.random.uniform(1000, 50000), -2)
            tx_data['transaction_type'] = TransactionType.WITHDRAW_CASH.value
            tx_data['fraud_description'] = "Agent fraud suspected - round amount manipulation"
        elif fraud_type == FraudType.ACCOUNT_TAKEOVER:
            tx_data['amount'] = round(np.random.uniform(10000, 80000), 2)
            tx_data['device_id'] = f"UNKNOWN_DEV_{random.randint(1000, 9999)}"
            tx_data['location'] = "UNKNOWN"
            tx_data['fraud_description'] = "Account takeover - dormant account activity"

        return tx_data

    def generate_dataset(
        self,
        days: int = 90,
        fraud_percentage: float = 0.03,
        save_to_file: bool = True
    ) -> pd.DataFrame:
        print(f"Generating {days} days of transaction data...")
        print(f"Target fraud percentage: {fraud_percentage:.2%}")

        transactions = []
        current_date = self.start_date
        # Estimate total transactions to prevent infinite loops
        avg_transactions_per_day = int(self.n_customers * 1.5)
        
        # Prepare fraud selection lists
        fraud_types = list(self.fraud_patterns.keys())
        raw_probs = [self.fraud_patterns[ft].probability for ft in fraud_types]
        total_prob = sum(raw_probs)
        fraud_probs = [p / total_prob for p in raw_probs]

        while current_date < self.end_date and len(transactions) < days * avg_transactions_per_day:
            daily_transactions = np.random.poisson(avg_transactions_per_day)
            
            for _ in range(daily_transactions):
                customer_id = random.choice(list(self.customer_profiles.keys()))
                profile = self.customer_profiles[customer_id]

                hour = np.random.choice(profile.typical_transaction_times) if profile.typical_transaction_times else np.random.randint(8, 20)
                timestamp = current_date.replace(
                    hour=int(hour),
                    minute=np.random.randint(0, 60),
                    second=np.random.randint(0, 60)
                )

                if np.random.random() < fraud_percentage:
                    # FIX: Use random.choices (standard library) to preserve Enum type
                    fraud_type = random.choices(fraud_types, weights=fraud_probs, k=1)[0]
                    
                    transaction = self._generate_fraud_transaction(customer_id, timestamp, fraud_type)
                    self.stats['fraudulent_transactions'] += 1
                else:
                    transaction = self._generate_normal_transaction(customer_id, timestamp, profile)

                transactions.append(transaction)
                self.stats['total_transactions'] += 1
                self.stats['total_amount'] += transaction['amount']

            current_date += timedelta(days=1)

        df = pd.DataFrame(transactions)
        if save_to_file:
            self._save_dataset(df)

        return df
    

    def _save_dataset(self, df: pd.DataFrame):
        data_dir = Path("data/synthetic")
        data_dir.mkdir(parents=True, exist_ok=True)

        csv_path = data_dir / "mpesa_transactions.csv"
        df.to_csv(csv_path, index=False)

        metadata = {
            'generation_date': datetime.now().isoformat(),
            'total_transactions': len(df),
            'fraudulent_transactions': int(df['is_fraud'].sum()),
            'fraud_rate': float(df['is_fraud'].mean()),
            'columns': df.columns.tolist(),
            'fraud_distribution': df['fraud_type'].value_counts().to_dict(),
            'transaction_type_distribution': df['transaction_type'].value_counts().to_dict(),
        }

        metadata_path = data_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        sample_path = data_dir / "sample_transactions.csv"
        df.head(1000).to_csv(sample_path, index=False)

        print(f"Data saved to: {csv_path}, metadata: {metadata_path}, sample: {sample_path}")
        return csv_path, metadata_path


# Quick helper
def generate_sample_data(
    output_path: str = "data/synthetic/mpesa_sample.csv",
    n_customers: int = 1000,
    days: int = 30,
    fraud_percentage: float = 0.03
) -> pd.DataFrame:
    generator = MPesaDataGenerator(n_customers=n_customers)
    df = generator.generate_dataset(days=days, fraud_percentage=fraud_percentage)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Sample data saved to: {output_path}")
    return df


if __name__ == "__main__":
    df = generate_sample_data(n_customers=500, days=7, fraud_percentage=0.05)
    print(df[['transaction_id', 'timestamp', 'customer_id', 'amount', 'is_fraud', 'fraud_type']].head())
