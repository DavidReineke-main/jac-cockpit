# Entries form

The cockpit stores staffing, checklists, flight settings, the deployment cycle and access by rank as "entries". A Google Form is the write path and its response sheet is the store, so the sheets stay the only backend.

## Set it up

1. In Google Drive create a form named **JAC Cockpit entries**.
2. Add three questions, all **Short answer** except the last, all optional:
   1. `type`
   2. `key`
   3. `payload` as **Paragraph**
3. Settings → Responses: turn **off** "Collect email addresses" and "Limit to 1 response". Nobody needs to sign in.
4. Responses → **Link to Sheets** → create a new spreadsheet.
5. In the new sheet: Share → General access → **Anyone with the link: Viewer**.
6. Send the cockpit maintainer:
   - the form's **public link** (Send → link icon), which looks like `https://docs.google.com/forms/d/e/<long id>/viewform`
   - the **response sheet link**.

The maintainer reads the three `entry.<number>` field ids from the form page and fills in `ENTRIES` near the top of `index.html`:

```js
const ENTRIES={
  post:'https://docs.google.com/forms/d/e/<long id>/formResponse',
  fields:{type:'entry.111',key:'entry.222',payload:'entry.333'},
  sheet:{id:'<response sheet id>',gid:'<gid of the responses tab>'}
};
```

## How it behaves

- Saving posts one row to the form. Reading takes the newest row per `type` and `key`.
- The form has no sign-in, so anyone with the page could add rows. That is acceptable for a prototype; the hosted version replaces this with Google sign-in.
- Old rows stay in the sheet as history. They can be deleted at any time; only the newest row per key matters.

## Entry types

| type | key | payload |
|---|---|---|
| `staffing` | `2026-11-21\|18A` | crews with callsign, channel and Pilot, CoPilot, Loadmaster; WARNO, OPO and CEFO links; notes |
| `check` | `2026-11-21` | ticked checklist items per unit |
| `setting` | `cas\|18A`, `cefo` | who makes sure reinsert reports are filed; default CEFO link |
| `cycle` | `cycle` | anchor Monday and the list of blocks |
| `roles` | `18`, `662`, `ALIC` | access matrix by rank |
