package workflows

import "github.com/google/uuid"

type NodeApp interface {
	Execute(input interface{}) (output interface{}, err error)
}
type Node struct {
	ID      string
	App     NodeApp
	Next    *Node
	Prev    *Node
	Inbox   chan interface{}
	Outbox  chan interface{}
	Trigger func() error
}
type NodeFactory func() NodeApp

type WorkFlow struct {
	Head Node
	Tail Node
}

func NewNode() Node {
	return Node{
		ID:     uuid.New().String(),
		App:    nil,
		Next:   nil,
		Prev:   nil,
		Inbox:  make(chan interface{}),
		Outbox: make(chan interface{}),
	}
}

func NewWorkFlow() WorkFlow {
	return WorkFlow{}
}

func (wf *WorkFlow) AddHead(app NodeApp) {
	wf.Head = Node{
		ID:   uuid.New().String(),
		App:  app,
		Next: nil,
		Prev: nil,
	}
}

func (wf *WorkFlow) AddTail(app NodeApp) {
	wf.Tail = Node{
		ID:   uuid.New().String(),
		App:  app,
		Next: nil,
		Prev: nil,
	}

}

func (wf WorkFlow) Execute(input interface{}) (output interface{}, err error) {
	return wf.Head.App.Execute(input)
}
