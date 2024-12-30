package main

import (
	"log"

	"github.com/ivikasavnish/workflowapp/workflows"
)

func main() {
	n := workflows.NewNode()
	n.Trigger = func() error {
		log.Println("Triggered")
		return nil

	}
	log.Println(n)
	wf := workflows.NewWorkFlow()
	log.Println(wf)
	wf.Run(n.App)

}
