---- MODULE Upload ----
\* Model of uploader/session.py. Each action is one Session method.
VARIABLES state, tempFile, published
vars == <<state, tempFile, published>>

States == {"idle", "uploading", "publishing", "committed", "cancelled"}

Init == /\ state = "idle"
        /\ tempFile = FALSE
        /\ published = FALSE

\* Session.start
Start == /\ state = "idle"
         /\ state' = "uploading"
         /\ tempFile' = TRUE
         /\ UNCHANGED published

\* Session.publish
Publish == /\ state = "uploading"
           /\ state' = "publishing"
           /\ published' = TRUE
           /\ UNCHANGED tempFile

\* Session.mark_committed
MarkCommitted == /\ state = "publishing"
                 /\ state' = "committed"
                 /\ tempFile' = FALSE
                 /\ UNCHANGED published

\* Session.cancel (the UI's cancel button)
Cancel == /\ state \in {"uploading", "publishing"}
          /\ state' = "cancelled"
          /\ tempFile' = FALSE
          /\ UNCHANGED published

\* Finished sessions stay finished.
Done == /\ state \in {"committed", "cancelled"}
        /\ UNCHANGED vars

Next == Start \/ Publish \/ MarkCommitted \/ Cancel \/ Done

Spec == Init /\ [][Next]_vars

TypeOK == /\ state \in States
          /\ tempFile \in BOOLEAN
          /\ published \in BOOLEAN

\* What the user is promised: a cancelled upload never leaves a published file.
CancelledIsUnpublished == state = "cancelled" => ~published
====
