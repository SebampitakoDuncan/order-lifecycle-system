#!/usr/bin/env python3
"""
Demo script for Order Lifecycle System.
Shows all API functionality with copy-paste examples.
"""

import requests
import time
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_command(title, command):
    print(f"\n📋 {title}:")
    print("-" * 40)
    print(command)

def demo_api():
    """Demonstrate all API functionality."""
    
    print_section("Order Lifecycle System - API Demo")
    print(f"Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Generate unique order ID
    order_id = f"demo-order-{int(time.time())}"
    
    # 1. Health Check
    print_section("1. Health Check")
    print_command("Check system health", f"curl {API_BASE}/health")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 2. Start Order Workflow
    print_section("2. Start Order Workflow")
    start_command = f'''curl -X POST "{API_BASE}/orders/{order_id}/start" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "initial_address": {{
      "street": "123 Demo Street",
      "city": "Demo City",
      "state": "DC",
      "zip": "12345"
    }}
  }}' '''
    
    print_command("Start new order", start_command)
    
    try:
        response = requests.post(
            f"{API_BASE}/orders/{order_id}/start",
            json={
                "initial_address": {
                    "street": "123 Demo Street",
                    "city": "Demo City",
                    "state": "DC",
                    "zip": "12345"
                }
            }
        )
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # 3. Get Order Status
    print_section("3. Get Order Status")
    status_command = f"curl {API_BASE}/orders/{order_id}/status"
    print_command("Check order status", status_command)
    
    try:
        response = requests.get(f"{API_BASE}/orders/{order_id}/status")
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 4. Update Address
    print_section("4. Update Shipping Address")
    update_command = f'''curl -X POST "{API_BASE}/orders/{order_id}/signals/update-address" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "new_address": {{
      "street": "456 Updated Avenue",
      "city": "Updated City",
      "state": "UC",
      "zip": "54321"
    }},
    "updated_by": "demo_user"
  }}' '''
    
    print_command("Update shipping address", update_command)
    
    try:
        response = requests.post(
            f"{API_BASE}/orders/{order_id}/signals/update-address",
            json={
                "new_address": {
                    "street": "456 Updated Avenue",
                    "city": "Updated City",
                    "state": "UC",
                    "zip": "54321"
                },
                "updated_by": "demo_user"
            }
        )
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 5. Cancel Order
    print_section("5. Cancel Order")
    cancel_command = f'''curl -X POST "{API_BASE}/orders/{order_id}/signals/cancel" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "reason": "Demo cancellation",
    "cancelled_by": "demo_user"
  }}' '''
    
    print_command("Cancel order", cancel_command)
    
    try:
        response = requests.post(
            f"{API_BASE}/orders/{order_id}/signals/cancel",
            json={
                "reason": "Demo cancellation",
                "cancelled_by": "demo_user"
            }
        )
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 6. Get Final Status
    print_section("6. Get Final Status")
    print_command("Check final status", f"curl {API_BASE}/orders/{order_id}/status")
    
    try:
        response = requests.get(f"{API_BASE}/orders/{order_id}/status")
        print(f"✅ Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 7. List All Orders
    print_section("7. List All Orders")
    list_command = f"curl {API_BASE}/orders"
    print_command("List all orders", list_command)
    
    try:
        response = requests.get(f"{API_BASE}/orders")
        data = response.json()
        print(f"✅ Response: {data['total_orders']} total orders")
        print(f"   Latest orders:")
        for order in data['orders'][:3]:  # Show first 3
            print(f"   - {order['order_id']}: {order['status']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 8. Performance Test
    print_section("8. Performance Test")
    print_command("Test 15-second constraint", "python3 test_15_second_constraint.py")
    
    print(f"\n🎉 Demo completed! Order ID: {order_id}")
    print(f"\n📊 Summary:")
    print(f"   - API Base URL: {API_BASE}")
    print(f"   - Interactive Docs: {API_BASE}/docs")
    print(f"   - Temporal UI: http://localhost:8080")
    print(f"   - Health Check: {API_BASE}/health")

if __name__ == "__main__":
    demo_api()
