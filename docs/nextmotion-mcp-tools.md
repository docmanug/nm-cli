# Nextmotion MCP Tools — nm-cli Reference

Outils Nextmotion disponibles via le MCP NextCall (`mcp.nextmotion.net/mcp`).

## Patients

### `nm_patient_retrieve`
Retrieve a Nextmotion patient by ID.

| Param | Type | Required | Description |
|---|---|---|---|
| `patient_id` | string | yes | Patient ID |

**CLI**: `nm nextcall patient get <patient_id>`

### `nm_chat_contact_search`
Search chat contacts in a Nextmotion clinic (used for patient search).

| Param | Type | Required | Description |
|---|---|---|---|
| `clinic_id` | string | yes | Nextmotion clinic ID |
| `search` | string | no | Name or phone number |
| `user_type` | number | no | 2 for patients |

**CLI**: `nm nextcall patient search <nom>`

## Devis (Quotes)

### `nm_quote_list`
List quotes for a Nextmotion clinic.

| Param | Type | Required | Description |
|---|---|---|---|
| `clinic_id` | string | yes | Nextmotion clinic ID |
| `limit` | number | no | Max results (default 50, max 100) |
| `offset` | number | no | Pagination offset (default 0) |

**CLI**: `nm nextcall quote list [--limit 50] [--offset 0]`

### `nm_quote_retrieve`
Retrieve details of a Nextmotion quote.

| Param | Type | Required | Description |
|---|---|---|---|
| `quote_id` | string | yes | Quote ID |

**CLI**: `nm nextcall quote get <quote_id>`

### `nm_quote_update_followup`
Update follow-up fields on a quote. Do NOT pass treatments or pricing fields.

| Param | Type | Required | Description |
|---|---|---|---|
| `quote_id` | string | yes | Quote ID |
| `last_follow_up_time` | string | no | ISO 8601 datetime |
| `next_follow_up_time` | string | no | ISO 8601 datetime |
| `follow_up_count` | number | no | Follow-up count |
| `last_channel_used` | string | no | Channel used |
| `response_received` | boolean | no | Response received flag |
| `response_time` | string | no | ISO 8601 datetime |
| `last_contact_time` | string | no | ISO 8601 datetime |

**CLI**: `nm nextcall quote update-followup <quote_id> [--next <datetime>] [--last <datetime>] [--channel whatsapp] [--count 3] [--responded true]`

## Chat

### `nm_chat_send_message`
Send a WhatsApp, SMS, or internal message to a Nextmotion chat contact.

| Param | Type | Required | Description |
|---|---|---|---|
| `contact_id` | string | yes | Chat contact ID |
| `text_body` | string | yes | Message text |
| `system` | enum | yes | `whatsapp`, `sms`, or `internal` |
| `clinic_id` | string | no | Clinic ID |

**CLI**: `nm nextcall chat send <contact_id> "message" [--channel whatsapp|sms|internal]`

## Labels

### `nm_object_label_list`
List labels (quote channels, tags, etc.) for a Nextmotion clinic.

| Param | Type | Required | Description |
|---|---|---|---|
| `clinic_id` | string | yes | Nextmotion clinic ID |
| `type` | string | no | Label type, e.g. `quote_channel` |

**CLI**: `nm nextcall labels list [--type quote_channel]`

## Contacts (NextCall)

### `contacts_create`
Create a new contact. Phone is normalized to E.164.

| Param | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Contact name |
| `phone` | string | yes | Phone number |
| `email` | string | no | Email |
| `company` | string | no | Company |
| `notes` | string | no | Notes |

**CLI**: `nm nextcall contacts create <name> <phone> [--email ...] [--company ...]`

### `contacts_update`
Update an existing contact by ID.

| Param | Type | Required | Description |
|---|---|---|---|
| `contactId` | string | yes | Contact ID |
| `name` | string | no | Name |
| `phone` | string | no | Phone |
| `email` | string | no | Email |
| `company` | string | no | Company |

**CLI**: `nm nextcall contacts update <contact_id> [--name ...] [--phone ...] [--email ...]`

## Calls (NextCall)

### `calls_initiate`
Start an outbound call.

| Param | Type | Required | Description |
|---|---|---|---|
| `userId` | string | yes | User ID (auto from profile) |
| `phoneNumber` | string | no | Phone to call |
| `contactId` | string | no | Contact ID |

**CLI**: `nm nextcall calls initiate <phone> [--contact <id>]`

### `calls_end`
End an active call.

| Param | Type | Required | Description |
|---|---|---|---|
| `callId` | string | yes | Call ID |

**CLI**: `nm nextcall calls end <call_id>`

## Calendar (NextCall)

### `calendar_update_event`
Update a Google Calendar event.

| Param | Type | Required | Description |
|---|---|---|---|
| `userId` | string | yes | User ID (auto) |
| `eventId` | string | yes | Event ID |
| `summary` | string | no | Title |
| `startDateTime` | string | no | Start datetime |
| `endDateTime` | string | no | End datetime |
| `description` | string | no | Description |
| `attendeeEmail` | string | no | Attendee email |

**CLI**: `nm nextcall calendar update <event_id> [--summary ...] [--start ...] [--end ...]`

### `calendar_delete_event`
Delete a Google Calendar event.

| Param | Type | Required | Description |
|---|---|---|---|
| `userId` | string | yes | User ID (auto) |
| `eventId` | string | yes | Event ID |

**CLI**: `nm nextcall calendar delete <event_id>`

### `calendar_freebusy`
Check availability (busy slots) in a time range.

| Param | Type | Required | Description |
|---|---|---|---|
| `userId` | string | yes | User ID (auto) |
| `timeMin` | string | yes | Start time |
| `timeMax` | string | yes | End time |

**CLI**: `nm nextcall calendar freebusy <date>`
