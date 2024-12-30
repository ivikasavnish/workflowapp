from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Any, Dict, Optional, Union
from datetime import datetime
import asyncio
from dataclasses import dataclass
import uuid

# Core message structure for node communication
@dataclass
class NodeMessage:
    id: str = str(uuid.uuid4())
    source_node: str = None
    target_node: str = None
    payload: Any = None
    timestamp: datetime = datetime.now()
    metadata: Dict = None

class NodeStatus(Enum):
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class PostBox:
    """Message handling system for nodes"""
    def __init__(self):
        self.inbox: asyncio.Queue[NodeMessage] = asyncio.Queue()
        self.outbox: asyncio.Queue[NodeMessage] = asyncio.Queue()
    
    async def send(self, message: NodeMessage):
        await self.outbox.put(message)
    
    async def receive(self) -> NodeMessage:
        return await self.inbox.get()
    
    async def process_message(self, message: NodeMessage) -> None:
        await self.inbox.put(message)

class BaseNode(ABC):
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.status = NodeStatus.READY
        self.postbox = PostBox()
        self.start_handlers = []
        self.end_handlers = []
        self.error_handlers = []

    async def start(self):
        """Initialize and start the node"""
        try:
            self.status = NodeStatus.STARTING
            await self._run_handlers(self.start_handlers)
            self.status = NodeStatus.RUNNING
            await self._process_loop()
        except Exception as e:
            self.status = NodeStatus.ERROR
            await self._handle_error(e)

    async def stop(self):
        """Gracefully stop the node"""
        self.status = NodeStatus.STOPPING
        await self._run_handlers(self.end_handlers)
        self.status = NodeStatus.STOPPED

    @abstractmethod
    async def process_message(self, message: NodeMessage) -> Optional[NodeMessage]:
        """Process incoming message and optionally return response"""
        pass

    async def _process_loop(self):
        """Main processing loop"""
        while self.status == NodeStatus.RUNNING:
            message = await self.postbox.receive()
            try:
                result = await self.process_message(message)
                if result:
                    await self.postbox.send(result)
            except Exception as e:
                await self._handle_error(e)

    async def _run_handlers(self, handlers: List[callable]):
        """Run list of handlers"""
        for handler in handlers:
            await handler()

    async def _handle_error(self, error: Exception):
        """Handle errors in the node"""
        for handler in self.error_handlers:
            await handler(error)

class WorkNode(BaseNode):
    """Node that performs actual work"""
    def __init__(self, node_id: str, work_func: callable):
        super().__init__(node_id)
        self.work_func = work_func
        self.next_nodes: List[str] = []

    async def process_message(self, message: NodeMessage) -> Optional[NodeMessage]:
        # Process the work
        result = await self.work_func(message.payload)
        
        # Create response message for next nodes
        if self.next_nodes:
            return NodeMessage(
                source_node=self.node_id,
                target_node=self.next_nodes[0],  # For simple chaining
                payload=result
            )
        return None

class RouterNode(BaseNode):
    """Node that routes messages based on conditions"""
    def __init__(self, node_id: str, routing_rules: Dict[callable, str]):
        super().__init__(node_id)
        self.routing_rules = routing_rules

    async def process_message(self, message: NodeMessage) -> Optional[NodeMessage]:
        # Check each rule and route accordingly
        for condition, target_node in self.routing_rules.items():
            if await condition(message.payload):
                return NodeMessage(
                    source_node=self.node_id,
                    target_node=target_node,
                    payload=message.payload
                )
        return None

class NodeNetwork:
    """Manages network of nodes and their connections"""
    def __init__(self):
        self.nodes: Dict[str, BaseNode] = {}
        self.message_bus = asyncio.Queue()

    def add_node(self, node: BaseNode):
        self.nodes[node.node_id] = node

    def connect_nodes(self, from_node_id: str, to_node_id: str):
        if from_node_id in self.nodes and to_node_id in self.nodes:
            from_node = self.nodes[from_node_id]
            if isinstance(from_node, WorkNode):
                from_node.next_nodes.append(to_node_id)

    async def start_network(self):
        """Start all nodes and message routing"""
        # Start message routing
        self.route_task = asyncio.create_task(self._route_messages())
        
        # Start all nodes
        node_tasks = [node.start() for node in self.nodes.values()]
        await asyncio.gather(*node_tasks)

    async def _route_messages(self):
        """Route messages between nodes"""
        while True:
            for node in self.nodes.values():
                if not node.postbox.outbox.empty():
                    message = await node.postbox.outbox.get()
                    if message.target_node in self.nodes:
                        target_node = self.nodes[message.target_node]
                        await target_node.postbox.process_message(message)

# Example usage:
async def example_work(data):
    # Simulate some work
    await asyncio.sleep(1)
    return f"Processed: {data}"

async def main():
    # Create nodes
    input_node = WorkNode("input", lambda x: x)
    process_node = WorkNode("process", example_work)
    output_node = WorkNode("output", print)

    # Create routing rules
    routing_rules = {
        lambda x: len(str(x)) > 10: "output",
        lambda x: True: "process"
    }
    router_node = RouterNode("router", routing_rules)

    # Set up network
    network = NodeNetwork()
    network.add_node(input_node)
    network.add_node(process_node)
    network.add_node(output_node)
    network.add_node(router_node)

    # Connect nodes
    network.connect_nodes("input", "router")
    network.connect_nodes("process", "output")

    # Start network
    await network.start_network()

    # Send test message
    test_message = NodeMessage(
        source_node="external",
        target_node="input",
        payload="Test data"
    )
    await input_node.postbox.process_message(test_message)

if __name__ == "__main__":
    asyncio.run(main())