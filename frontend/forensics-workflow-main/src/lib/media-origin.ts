import type { CallRecord, ContactRecord, MediaRecord, MessageRecord } from "@/services/forensics-api";

export function indexByKey<T>(items: T[], key: (item: T) => string | null | undefined): Map<string, T> {
  const map = new Map<string, T>();
  for (const item of items) {
    const k = key(item);
    if (k) map.set(k, item);
  }
  return map;
}

export function buildContactPhoneMap(contacts: ContactRecord[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const c of contacts) {
    if (c.phone && c.name) map.set(c.phone, c.name);
  }
  return map;
}

function resolveParty(phone: string | null, contactByPhone: Map<string, string>): string {
  if (!phone) return "Unknown";
  const name = contactByPhone.get(phone);
  return name ? `${name} (${phone})` : phone;
}

export function describeMediaOrigin(
  media: Pick<MediaRecord, "associated_message_id" | "associated_call_id">,
  messagesById: Map<string, MessageRecord>,
  callsById: Map<string, CallRecord>,
  contactByPhone: Map<string, string>,
): string {
  if (media.associated_message_id) {
    const msg = messagesById.get(media.associated_message_id);
    return msg
      ? `From: ${resolveParty(msg.sender, contactByPhone)} → ${resolveParty(msg.receiver, contactByPhone)} (Message ${msg.message_id})`
      : `Associated message ${media.associated_message_id} (not found)`;
  }
  if (media.associated_call_id) {
    const call = callsById.get(media.associated_call_id);
    return call
      ? `Call: ${resolveParty(call.caller, contactByPhone)} → ${resolveParty(call.callee, contactByPhone)} (Call ${call.call_id})`
      : `Associated call ${media.associated_call_id} (not found)`;
  }
  return "No associated message or call";
}
