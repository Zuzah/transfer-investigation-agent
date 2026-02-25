## What a human can now do that they couldn't before

Wealthsimple's own documentation admits it plainly: "At this stage, our support team doesn't have full visibility on the status of your transfer." When a client reports a stuck transfer, agents start from zero — manually piecing together timelines, guessing at failure points, drafting responses from memory. Resolution is slow, inconsistent, and entirely dependent on individual knowledge.
This system changes the starting point. The agent arrives at a decision, not a blank page.

## What the AI is responsible for?

The system takes a natural-language complaint and does the investigative work autonomously. It retrieves relevant transfer documentation using semantic search and reranking, reconstructs the expected timeline for that specific transfer type, identifies the most likely failure point — WS side, institution side, or client side — and produces a cited draft response with a confidence score and any escalation flags.

Diagnosis and drafting. That's the AI's job.

## Where the AI must stop

The AI does not send anything. Every draft requires human approval before it reaches a client.

More importantly, the AI never makes the remedy decision. Whether to waive a fee, offer compensation, or escalate requires judgment about client lifetime value, regulatory exposure, and institutional precedent — judgment that only makes sense with visibility across cases, not just this one. These decisions also create legal record. A human owns the outcome.

## What would break first at scale

The most dangerous failure mode is coordinated fraud disguised as legitimate transfer complaints. The AI reconstructs individual timelines well, but cross-case pattern recognition — distinguishing a real cluster of institutional failures from a fraud ring probing the system — requires a human investigator. The AI surfaces the signal. It can't make the call.

The second risk is knowledge base staleness. The system's accuracy depends entirely on current documentation. If WS changes a settlement workflow and the knowledge base isn't updated, the AI will confidently reconstruct the wrong timeline. Maintaining that documentation has to be an owned operational responsibility, not an assumption.

At scale, the bottleneck shifts from investigation speed to approval speed. That's a better problem — it's a process challenge, not a technical one. But it has to be designed for from day one.