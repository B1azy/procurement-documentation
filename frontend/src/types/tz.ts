export interface TZContent {
    general_info: any;
    object_description: any;
    work_items: { order: number; name: string; description: string | null }[];
    volumes: { name: string; unit: string; value: number | null; basis: string; basis_note: string | null }[];
    materials: { entries: string[]; notes: string | null };
    quality: { entries: string[]; notes: string | null };
    normative_references: { code: string; title: string; source: string; verified: boolean }[];
    deadlines: any;
    conditions: any;
    contractor_requirements: any;
    acceptance: { procedure: string | null; criteria: { text: string; measurable: boolean }[] };
    warranty: any;
    assumptions: { text: string; source: string; requires_check: boolean }[];
}

export interface Specification {
    id: string;
    purchase_id: string;
    version: number;
    content: TZContent;
    is_current: boolean;
    created_at: string;
    assumptions: { id: string; text: string; source: string; requires_check: boolean }[];
}