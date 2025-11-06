## This is the design of DB

```
   erDiagram
       USER {
           string user_id PK
           string user_name UK
           string user_password
       }
       
       SESSION {
           string session_id PK
           string user_id FK
           timestamp created_at
           timestamp last_active
           string session_state
       }
       
       MESSAGE {
           string message_id PK
           string session_id FK
           string sender_type
           string sender_id
           json content
           timestamp timestamp
       }
       
       AGENT_SCRATCHPAD {
           string scratchpad_id PK
           string session_id FK
           string agent_name
           string thought_type
           text content
           timestamp timestamp
       }

       USER ||--o{ SESSION : "has"
       SESSION ||--o{ MESSAGE : "contains"
       SESSION ||--o{ AGENT_SCRATCHPAD : "contains"
```
