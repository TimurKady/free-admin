# Cards Guide

## Quick Start

1. Register the card in `views.py`:

   ```python
   admin_site.register_card(
       key="thermo1",
       label="Demo",
       title="Temperature Sensor",
       template="cards/thermo.html",
       icon="bi-thermometer-half",
       channel="thermo-channel"
   )
   ```

2. Create `apps/demo/service.py`:

   ```python
   from contrib.admin.core.sse import PublisherService
   import asyncio, random


   class TemperaturePublisher(PublisherService):
       card_key = "thermo1"
       channel = "thermo-channel"

       def get_initial_state(self):
           return {"temp": 25.0} 

       async def run(self):
           while True:
               temp = random.uniform(25, 40)
               self.publish({"temp": temp})
               await asyncio.sleep(1)
   ```

3. Create the `templates/cards/thermo.html` template and extend `includes/cards.html`.
4. After the admin panel starts, the card will appear and update in real time.

## Architecture

- **CardManager** stores the state and exposes it via REST/SSE.
- **PublisherService** publishes the data.
- **UI (`Card.js`)** listens to SSE and updates the DOM.

`CardManager` persists card payloads in memory so every card can be restored even if
the admin dashboard reconnects. A `PublisherService` instance injects fresh
payloads into the manager by calling `self.publish(...)`. Each publish call
performs three coordinated actions: the payload is merged into the existing card
state, the updated snapshot becomes immediately available to REST consumers, and
an SSE event is fanned out so that connected browsers receive the change without
polling. This tight loop keeps long-running publishers and short-lived requests
in sync.

### Endpoints

- **REST** `GET /api/cards/{key}/state` returns the latest persisted card data
  from `CardManager`. It powers server-side rendering and is ideal for
  health-checks or debugging because it always returns the most recent snapshot.
- **SSE** `GET /api/cards/{key}/events` streams real-time updates. Every call to
  `PublisherService.publish()` yields an SSE message that the browser consumes to
  update the DOM incrementally.

### Coordination Flow

1. `PublisherService` gathers new domain data and calls `publish()`.
2. `CardManager` merges the payload, stores it, and broadcasts events.
3. The API layer exposes the new state via REST or pushes it via SSE.
4. `card.js` receives updates, hydrates card components, and manipulates the DOM.

Think of the lifecycle as: **PublisherService → CardManager → API → card.js → DOM**.

## Best Practices

- Always implement `get_initial_state()`.
- Use asynchronous operations inside `run()`.
- If the event source is external (Redis, RabbitMQ), subscribe within `run()`.
- Do not create a blocking `while True` without `await asyncio.sleep()` or `async for`.

## Examples

### Continuous sensor loop

```python
class TemperaturePublisher(PublisherService):
    card_key = "thermo1"
    channel = "thermo-channel"

    def get_initial_state(self):
        return {"temp": 25.0}

    async def run(self):
        async for temp in sensor.stream():
            self.publish({"temp": temp})
```

### Redis Pub/Sub listener

```python
class RedisPublisher(PublisherService):
    card_key = "redis-card"
    channel = "redis-channel"

    async def run(self):
        async with redis_client.pubsub() as pubsub:
            await pubsub.subscribe("metrics")
            async for message in pubsub.listen():
                payload = json.loads(message["data"])
                self.publish(payload)
```

### Timer-driven publisher

```python
class HeartbeatPublisher(PublisherService):
    card_key = "heartbeat"
    channel = "heartbeat-channel"

    def get_initial_state(self):
        return {"alive": True, "sequence": 0}

    async def run(self):
        sequence = 0
        while True:
            sequence += 1
            self.publish({"alive": True, "sequence": sequence})
            await asyncio.sleep(5)
```
