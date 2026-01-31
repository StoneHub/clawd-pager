import asyncio
from aioesphomeapi import APIClient

async def test_alert():
    client = APIClient("192.168.50.85", 6053, "")
    await client.connect(login=True)
    print("Connected!")
    
    services = await client.list_entities_services()
    alert_service = next((s for s in services[1] if s.name == "alert"), None)
    
    if alert_service:
        print(f"Found service: {alert_service}")
        # In this version of aioesphomeapi, execute_service is sync
        client.execute_service(alert_service, {"my_text": "Direct Alert! 🚀"})
        print("Alert sent!")
    else:
        print("Alert service not found!")
        print("Available services:", [s.name for s in services[1]])
        
    await asyncio.sleep(1) # Wait for message to send
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_alert())
