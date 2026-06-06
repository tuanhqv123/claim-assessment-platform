export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      assessments: {
        Row: {
          claim_id: string
          created_at: string
          guard_flags: Json
          id: string
          recommendation: Database["public"]["Enums"]["recommendation"] | null
          recommendation_reason: string | null
          report: Json | null
          tenant_id: string
          tool_call_log: Json | null
        }
        Insert: {
          claim_id: string
          created_at?: string
          guard_flags?: Json
          id?: string
          recommendation?: Database["public"]["Enums"]["recommendation"] | null
          recommendation_reason?: string | null
          report?: Json | null
          tenant_id: string
          tool_call_log?: Json | null
        }
        Update: {
          claim_id?: string
          created_at?: string
          guard_flags?: Json
          id?: string
          recommendation?: Database["public"]["Enums"]["recommendation"] | null
          recommendation_reason?: string | null
          report?: Json | null
          tenant_id?: string
          tool_call_log?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "assessments_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "assessments_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      claim_transitions: {
        Row: {
          claim_id: string
          created_at: string
          from_state: Database["public"]["Enums"]["claim_state"] | null
          id: number
          notes: string | null
          reason: string | null
          side_effects: Json
          tenant_id: string
          to_state: Database["public"]["Enums"]["claim_state"]
          triggered_by: string | null
          triggered_by_role: Database["public"]["Enums"]["app_role"] | null
        }
        Insert: {
          claim_id: string
          created_at?: string
          from_state?: Database["public"]["Enums"]["claim_state"] | null
          id?: never
          notes?: string | null
          reason?: string | null
          side_effects?: Json
          tenant_id: string
          to_state: Database["public"]["Enums"]["claim_state"]
          triggered_by?: string | null
          triggered_by_role?: Database["public"]["Enums"]["app_role"] | null
        }
        Update: {
          claim_id?: string
          created_at?: string
          from_state?: Database["public"]["Enums"]["claim_state"] | null
          id?: never
          notes?: string | null
          reason?: string | null
          side_effects?: Json
          tenant_id?: string
          to_state?: Database["public"]["Enums"]["claim_state"]
          triggered_by?: string | null
          triggered_by_role?: Database["public"]["Enums"]["app_role"] | null
        }
        Relationships: [
          {
            foreignKeyName: "claim_transitions_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "claim_transitions_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      claims: {
        Row: {
          amount: number
          claim_date: string | null
          claim_number: string
          claim_type: Database["public"]["Enums"]["claim_type"]
          created_at: string
          custom_fields: Json
          diagnosis_code: string | null
          diagnosis_description: string | null
          id: string
          info_request_count: number
          member_id: string | null
          policy_id: string | null
          procedure_codes: string[]
          provider: string | null
          sla_deadline: string | null
          state: Database["public"]["Enums"]["claim_state"]
          sub_benefit: string | null
          tenant_id: string
          updated_at: string
        }
        Insert: {
          amount?: number
          claim_date?: string | null
          claim_number: string
          claim_type: Database["public"]["Enums"]["claim_type"]
          created_at?: string
          custom_fields?: Json
          diagnosis_code?: string | null
          diagnosis_description?: string | null
          id?: string
          info_request_count?: number
          member_id?: string | null
          policy_id?: string | null
          procedure_codes?: string[]
          provider?: string | null
          sla_deadline?: string | null
          state?: Database["public"]["Enums"]["claim_state"]
          sub_benefit?: string | null
          tenant_id: string
          updated_at?: string
        }
        Update: {
          amount?: number
          claim_date?: string | null
          claim_number?: string
          claim_type?: Database["public"]["Enums"]["claim_type"]
          created_at?: string
          custom_fields?: Json
          diagnosis_code?: string | null
          diagnosis_description?: string | null
          id?: string
          info_request_count?: number
          member_id?: string | null
          policy_id?: string | null
          procedure_codes?: string[]
          provider?: string | null
          sla_deadline?: string | null
          state?: Database["public"]["Enums"]["claim_state"]
          sub_benefit?: string | null
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "claims_policy_id_fkey"
            columns: ["policy_id"]
            isOneToOne: false
            referencedRelation: "policies"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "claims_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      documents: {
        Row: {
          claim_id: string | null
          confidence: number | null
          created_at: string
          document_type: string | null
          file_name: string | null
          id: string
          issues: string[]
          ocr_result: Json | null
          status: Database["public"]["Enums"]["document_status"]
          storage_path: string | null
          tenant_id: string
        }
        Insert: {
          claim_id?: string | null
          confidence?: number | null
          created_at?: string
          document_type?: string | null
          file_name?: string | null
          id?: string
          issues?: string[]
          ocr_result?: Json | null
          status?: Database["public"]["Enums"]["document_status"]
          storage_path?: string | null
          tenant_id: string
        }
        Update: {
          claim_id?: string | null
          confidence?: number | null
          created_at?: string
          document_type?: string | null
          file_name?: string | null
          id?: string
          issues?: string[]
          ocr_result?: Json | null
          status?: Database["public"]["Enums"]["document_status"]
          storage_path?: string | null
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "documents_claim_id_fkey"
            columns: ["claim_id"]
            isOneToOne: false
            referencedRelation: "claims"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "documents_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      policies: {
        Row: {
          created_at: string
          data: Json
          id: string
          policy_number: string
          tenant_id: string
        }
        Insert: {
          created_at?: string
          data: Json
          id?: string
          policy_number: string
          tenant_id: string
        }
        Update: {
          created_at?: string
          data?: Json
          id?: string
          policy_number?: string
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "policies_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          created_at: string
          email: string | null
          full_name: string | null
          id: string
          role: Database["public"]["Enums"]["app_role"]
          tenant_id: string | null
        }
        Insert: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id: string
          role?: Database["public"]["Enums"]["app_role"]
          tenant_id?: string | null
        }
        Update: {
          created_at?: string
          email?: string | null
          full_name?: string | null
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          tenant_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "profiles_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      tenant_configs: {
        Row: {
          config: Json
          created_at: string
          created_by: string | null
          id: string
          is_active: boolean
          tenant_id: string
          version: number
        }
        Insert: {
          config: Json
          created_at?: string
          created_by?: string | null
          id?: string
          is_active?: boolean
          tenant_id: string
          version: number
        }
        Update: {
          config?: Json
          created_at?: string
          created_by?: string | null
          id?: string
          is_active?: boolean
          tenant_id?: string
          version?: number
        }
        Relationships: [
          {
            foreignKeyName: "tenant_configs_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      tenants: {
        Row: {
          created_at: string
          id: string
          name: string
          slug: string
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          slug: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          slug?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      app_role:
        | "document_clerk"
        | "assessor"
        | "team_lead"
        | "manager"
        | "director"
        | "committee"
        | "finance"
        | "admin"
      claim_state:
        | "SUBMITTED"
        | "DOCUMENTS_VERIFIED"
        | "UNDER_ASSESSMENT"
        | "PENDING_INFO"
        | "APPROVED"
        | "REJECTED"
        | "PAYMENT_INITIATED"
        | "CLOSED"
      claim_type:
        | "OUTPATIENT"
        | "INPATIENT"
        | "DENTAL"
        | "MATERNITY"
        | "OPTICAL"
      document_status: "COMPLETE" | "INCOMPLETE" | "MISSING" | "TYPE_MISMATCH"
      recommendation: "APPROVE" | "REJECT" | "REQUEST_MORE_INFO"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      app_role: [
        "document_clerk",
        "assessor",
        "team_lead",
        "manager",
        "director",
        "committee",
        "finance",
        "admin",
      ],
      claim_state: [
        "SUBMITTED",
        "DOCUMENTS_VERIFIED",
        "UNDER_ASSESSMENT",
        "PENDING_INFO",
        "APPROVED",
        "REJECTED",
        "PAYMENT_INITIATED",
        "CLOSED",
      ],
      claim_type: ["OUTPATIENT", "INPATIENT", "DENTAL", "MATERNITY", "OPTICAL"],
      document_status: ["COMPLETE", "INCOMPLETE", "MISSING", "TYPE_MISMATCH"],
      recommendation: ["APPROVE", "REJECT", "REQUEST_MORE_INFO"],
    },
  },
} as const
