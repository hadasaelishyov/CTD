# bus.py

class Event:
    def __init__(self, name, data):
        self.name = name
        self.data = data


class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_name, handler):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler)

    def publish(self, event: Event):
        handlers = self.subscribers.get(event.name, [])
        for handler in handlers:
            handler(event)
