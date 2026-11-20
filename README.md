# ShilpSaathi

**One voice note. Two taps. From workshop to buyer.**

An AI agent that helps artisans and weavers sell directly to buyers who value their craft. Built for the Tech4Bharat GAVS Hackathon, **Problem 7.1** (Agentic AI). Prototype round.

**Team:** [team name] | [member names]
**Status:** Prototype. See "What is real vs. simulated" below.

---

## The problem

Artisans sell mostly through traders and local fairs. Listing online needs photography and digital skills, the craft's story and the maker's name get lost, and bulk negotiation happens without market-rate information. Margins stay thin and middlemen keep the larger share.

## What ShilpSaathi does

The artisan's whole product is **one voice note and two taps**. No app, no forms, no typing.

1. **Send** photos and a voice note in your own language on a chat app.
2. **Tap** to approve the ready listing: a faithful description, the maker's story, and a fair price band.
3. **Tap** to approve, edit or decline each buyer proposal.

Buyers post a requirement. A matching agent shortlists artisans and drafts a proposal. Nothing reaches the buyer until the artisan approves.

## Design principles

- **Agents propose, humans commit.** No price, quantity or deadline is committed without the maker's explicit approval.
- **Faithfulness Guard.** Every claim in a listing must trace to something the artisan said or a photo observation they confirmed. Unsupported claims (heritage, "organic", certifications) are blocked.
- **Approval Gate.** A state machine in code, not a prompt. Expired requests never auto-approve, and any later change to terms needs fresh approval.
- **Grounded pricing.** Code computes the price from cost and cited comparables, with a confidence level. The model only explains it. When data is thin, the system says so.
- **Maker's name stays attached** to the product everywhere it appears.

## How it works

```
Artisan (voice + photos)
   -> Channel adapter (WhatsApp / Telegram)
   -> Orchestrator (state machine)
   -> Agents: Intake, Vision, Story, Pricing, Matching, Negotiation
   -> Faithfulness Guard
   -> Approval Gate -> Artisan taps Approve / Edit / Decline
   -> Published to buyer feed + story page (QR)
```

Full design, data model, flows and evaluation plan: [ARCHITECTURE.md](./Architecture.md)

## What is real vs. simulated

| Area | Prototype status |
|---|---|
| Voice and photo intake | Real |
| Faithfulness Guard with claim trace | Real |
| Pricing logic with cited comparables | Real logic, **seed data** |
| Approval Gate and audit log | Real |
| Story page with QR | Real |
| Buyer feed and requirement-to-proposal flow | Real, minimal |
| Market comparables | **Simulated** (curated seed set) |
| Artisans and buyers | **Simulated** (test personas) |
| Open-network listing, UPI payments, logistics | Not built (roadmap) |

We make no claim of real-world income uplift. All numbers shown in the demo are prototype measurements on seed data.

## Tech stack

Multimodal LLM with schema-constrained outputs, Indic speech-to-text and text-to-speech, FastAPI orchestrator with a state machine, Postgres with pgvector, object storage, chat-channel adapter. [Edit to match what you actually built.]

## Run locally

```
[add your commands, e.g. docker compose up]
```

## Demo

[Link to demo video or live demo, if any]

## Assumptions we still need to validate

- Artisans (or a household proxy) are comfortable with voice notes on a chat app.
- Usable market comparables can be sourced legally and reliably.
- Speech-to-text quality holds up for real regional accents and noisy environments.
- Buyers will trust a maker-approved listing and story over a plain one.

## Roadmap

Field validation with real artisans, live comparables pipeline, cooperative admin dashboard, open-network seller integration, UPI payment links with maker-approved payee, document-verified provenance tiers, logistics.

## How this fits the existing ecosystem

ShilpSaathi is not another marketplace. It is the voice-first agent that creates a faithful listing and a defensible price, and it is designed to feed existing channels such as open-network marketplaces later.

## References

Context sources. Figures are as reported by these sources and have not been independently verified by us.

- India Development Review (Jan 2023), "Indian artisans are still missing from e-commerce platforms": https://idronline.org/article/ecosystem-development/indian-artisans-are-still-missing-from-e-commerce-platforms/
- Alliance Magazine, on handicraft e-commerce and the Open Network for Digital Commerce: https://alliancemagazine.org/?p=322995
- Sattva, "Crafting the E-Commerce Path for Artisans with the Open Network for Digital Commerce": https://www.sattva.co.in/ski/crafting-the-e-commerce-path-for-artisans-with-the-open-network-for-digital-commerce/
- Office of the Development Commissioner (Handicrafts), Indian Handicraft Portal: http://indian.handicrafts.gov.in

## License

[Add a license, e.g. MIT, or state "All rights reserved" for the prototype.]
