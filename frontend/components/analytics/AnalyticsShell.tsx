"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { AtSign, Link2, Loader2, Pencil, X } from "lucide-react";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { AccountSettings } from "@/types";

type AnalyticsAccountContextValue = {
  settings: AccountSettings | null;
  loading: boolean;
  refresh: () => Promise<void>;
  configured: boolean;
};

const AnalyticsAccountContext = createContext<AnalyticsAccountContextValue | null>(null);

export function useAnalyticsAccount() {
  const ctx = useContext(AnalyticsAccountContext);
  if (!ctx) {
    throw new Error("useAnalyticsAccount must be used within AnalyticsShell");
  }
  return ctx;
}

export function AnalyticsShell({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [handleInput, setHandleInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [changingAccount, setChangingAccount] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const st = await api.analyticsAccountSettings();
      setSettings(st);
      setHandleInput(st.tiktok_handle ?? "");
      setConnectError(null);
    } catch (e) {
      setConnectError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const configured = settings?.configured ?? false;

  const saveAccount = async () => {
    const trimmed = handleInput.trim().replace(/^@/, "");
    if (!trimmed) {
      setConnectError("Enter your TikTok @handle.");
      return;
    }
    setSaving(true);
    try {
      const st = await api.updateAnalyticsAccount(trimmed);
      setSettings(st);
      setHandleInput(st.tiktok_handle ?? trimmed);
      setChangingAccount(false);
      setConnectError(null);
    } catch (e) {
      setConnectError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const value = useMemo(
    () => ({ settings, loading, refresh, configured }),
    [settings, loading, refresh, configured],
  );

  return (
    <AnalyticsAccountContext.Provider value={value}>
      {configured ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/40 px-4 py-3">
          <div className="flex items-center gap-2 text-sm">
            <AtSign className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Connected account</span>
            <span className="font-semibold">@{settings?.tiktok_handle}</span>
            {settings?.source === "environment" ? (
              <span className="text-xs text-muted-foreground">(env)</span>
            ) : null}
          </div>
          {!changingAccount ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8"
              onClick={() => setChangingAccount(true)}
            >
              <Pencil className="mr-1.5 h-3.5 w-3.5" />
              Change account
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8"
              onClick={() => {
                setChangingAccount(false);
                setHandleInput(settings?.tiktok_handle ?? "");
                setConnectError(null);
              }}
            >
              <X className="mr-1.5 h-3.5 w-3.5" />
              Cancel
            </Button>
          )}
        </div>
      ) : null}

      {(!configured || changingAccount) && !loading ? (
        <Card className="mb-6 border-primary/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Link2 className="h-4 w-4" />
              {configured ? "Change TikTok account" : "Connect your TikTok account"}
            </CardTitle>
            <CardDescription>
              Enter the @handle for the account you analyze (without the @). Public video data
              is loaded via tikwm when available; you can always enter Studio metrics manually.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-2">
                <Label htmlFor="analytics-tiktok-handle">TikTok handle</Label>
                <div className="flex">
                  <span className="inline-flex items-center rounded-l-md border border-r-0 border-input bg-muted px-3 text-sm text-muted-foreground">
                    @
                  </span>
                  <Input
                    id="analytics-tiktok-handle"
                    value={handleInput}
                    onChange={(e) => setHandleInput(e.target.value)}
                    placeholder="yourbrand"
                    className="rounded-l-none"
                  />
                </div>
              </div>
              <Button onClick={saveAccount} disabled={saving}>
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {configured ? "Update account" : "Save account"}
              </Button>
            </div>
            {connectError ? (
              <p className="mt-3 text-sm text-red-600">{connectError}</p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <AnalyticsNav />
      {children}
    </AnalyticsAccountContext.Provider>
  );
}
