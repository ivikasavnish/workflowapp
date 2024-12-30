package nodes

type Node interface {
	Execute(input interface{}) (output interface{}, err error)
}

type NodeFactory func() Node
