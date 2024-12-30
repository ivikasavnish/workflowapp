from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Any, Dict, Optional
from datetime import datetime
import asyncio

# Enums for different types of triggers and states
class TriggerType(Enum):
    HTTP_REQUEST = "http_request"
    WEBSOCKET = "websocket"
    MESSAGE_QUEUE = "message_queue"
    SCHEDULED = "scheduled"
    CRON = "cron"

class NodeState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"

class NodeType(Enum):
    STARTER = "starter"
    INNER = "inner"
    TERMINAL = "terminal"

# Base Node Interface
class Node(ABC):
    def __init__(self, node_id: str, node_type: NodeType):
        self.node_id = node_id
        self.node_type = node_type
        self.state = NodeState.IDLE
        self.next_nodes: List[Node] = []
        self.previous_nodes: List[Node] = []
        self.created_at = datetime.now()
        self.last_run = None
        self.result = None

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process the input data and return result"""
        pass

    @abstractmethod
    async def validate_input(self, input_data: Any) -> bool:
        """Validate the input before processing"""
        pass

    def add_next_node(self, node: 'Node') -> None:
        self.next_nodes.append(node)
        node.previous_nodes.append(self)

    async def execute(self, input_data: Any) -> Any:
        try:
            self.state = NodeState.RUNNING
            
            if not await self.validate_input(input_data):
                raise ValueError(f"Invalid input for node {self.node_id}")

            self.result = await self.process(input_data)
            self.state = NodeState.COMPLETED
            self.last_run = datetime.now()

            # Execute next nodes
            return await self.execute_next_nodes(self.result)

        except Exception as e:
            self.state = NodeState.FAILED
            raise

    async def execute_next_nodes(self, input_data: Any) -> List[Any]:
        if not self.next_nodes:
            return [input_data]

        tasks = [node.execute(input_data) for node in self.next_nodes]
        return await asyncio.gather(*tasks)

# Example implementations for different node types

class HTTPStarterNode(Node):
    def __init__(self, node_id: str, endpoint: str):
        super().__init__(node_id, NodeType.STARTER)
        self.endpoint = endpoint
        self.trigger_type = TriggerType.HTTP_REQUEST

    async def validate_input(self, input_data: Dict) -> bool:
        return isinstance(input_data, dict)

    async def process(self, input_data: Dict) -> Dict:
        # Process HTTP request data
        return input_data

class MessageQueueNode(Node):
    def __init__(self, node_id: str, queue_name: str):
        super().__init__(node_id, NodeType.INNER)
        self.queue_name = queue_name
        self.trigger_type = TriggerType.MESSAGE_QUEUE

    async def validate_input(self, input_data: Any) -> bool:
        return True

    async def process(self, input_data: Any) -> Any:
        # Process message queue data
        return input_data

class TerminalNode(Node):
    def __init__(self, node_id: str):
        super().__init__(node_id, NodeType.TERMINAL)

    async def validate_input(self, input_data: Any) -> bool:
        return True

    async def process(self, input_data: Any) -> Any:
        # Final processing
        return input_data

# Flow management class
class NodeFlowManager:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def connect_nodes(self, from_node_id: str, to_node_id: str) -> None:
        from_node = self.nodes.get(from_node_id)
        to_node = self.nodes.get(to_node_id)
        
        if from_node and to_node:
            from_node.add_next_node(to_node)

    async def execute_flow(self, starter_node_id: str, input_data: Any) -> Any:
        starter_node = self.nodes.get(starter_node_id)
        if not starter_node:
            raise ValueError(f"Starter node {starter_node_id} not found")
        
        return await starter_node.execute(input_data)

# Example usage:
async def main():
    # Create nodes
    http_starter = HTTPStarterNode("starter1", "/api/start")
    queue_processor = MessageQueueNode("processor1", "main_queue")
    terminal = TerminalNode("terminal1")

    # Set up flow manager
    flow_manager = NodeFlowManager()
    flow_manager.add_node(http_starter)
    flow_manager.add_node(queue_processor)
    flow_manager.add_node(terminal)

    # Connect nodes
    flow_manager.connect_nodes("starter1", "processor1")
    flow_manager.connect_nodes("processor1", "terminal1")

    # Execute flow
    input_data = {"request": "test"}
    result = await flow_manager.execute_flow("starter1", input_data)
    print(f"Flow execution result: {result}")

# Run the example
if __name__ == "__main__":
    asyncio.run(main())