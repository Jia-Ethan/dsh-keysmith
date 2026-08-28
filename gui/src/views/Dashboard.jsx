import React from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, AlertTriangle, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { fetchStatus, isTauriMissing } from "@/lib/api";
import { useAppState } from "@/hooks/useAppState";
import { setLastStatus, setView } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FadeIn } from "@/components/FadeIn";
import { StatusPill } from "@/components/StatusPill";
import { RawJson } from "@/components/ReportView";
import { cn } from "@/lib/utils";

const ADAPTER_VARIANT = {
  patched: "green",
  pristine: "yellow",
  unknown: "yellow",
  absent: "gray",
};

export function Dashboard() {
  const { t } = useTranslation();
  const { cliInfo, lastStatus } = useAppState();
  const [status, setStatus] = React.useState(lastStatus);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchStatus();
      setStatus(next);
      setLastStatus(next);
    } catch (err) {
      if (isTauriMissing(err)) return;
      setError(err instanceof Error ? err : new Error(String(err)));
      toast.error(t("dash.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  React.useEffect(() => {
    if (cliInfo.checked && cliInfo.path && !status) refresh();
  }, [cliInfo.checked, cliInfo.path]); // eslint-disable-line react-hooks/exhaustive-deps

  const cliChecking = !cliInfo.checked;
  const noCli = cliInfo.checked && !cliInfo.path && !cliInfo.error;
  const cliFailed = cliInfo.checked && !cliInfo.path && !!cliInfo.error;
  const adapter = status?.adapterPatch;

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <FadeIn>
          <h1 className="text-2xl font-semibold tracking-tight">{t("dash.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {cliChecking && t("dash.loading")}
            {cliInfo.path && t("dash.summary", {
              cliVer: cliInfo.version || t("common.unknown"),
              runtime: cliInfo.runtime || t("common.unknown"),
            })}
          </p>
        </FadeIn>
        <Button size="sm" variant="secondary" onClick={refresh} disabled={loading || !cliInfo.path}>
          <RefreshCw className={cn("size-3.5", loading && "animate-spin")} aria-hidden="true" />
          {t("dash.refresh")}
        </Button>
      </div>

      {(noCli || cliFailed) && (
        <FadeIn>
          <section className="card-glass p-5">
            <p className="text-sm">{cliFailed ? t("dash.cliCheckFailed") : t("dash.noCli")}</p>
            <p className="mt-3 text-xs text-muted-foreground">{t("dash.getCliTitle")}</p>
            <p className="mt-1 text-xs">
              <a
                href="https://github.com/Jia-Ethan/dsh-keysmith"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 font-mono text-accent hover:text-accent-hover"
              >
                {t("dash.getCliLink")}
                <ExternalLink className="size-3" aria-hidden="true" />
              </a>
            </p>
            <Button size="sm" className="mt-3" onClick={() => setView("settings")}>{t("dash.noCliAction")}</Button>
          </section>
        </FadeIn>
      )}

      {error && (
        <p className="mb-4 flex items-start gap-2 text-sm text-danger">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {error.message}
        </p>
      )}

      {status && (
        <FadeIn>
          <section className="card-glass p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <StatusPill health={status.health} />
              <span className="font-mono text-xs text-muted-foreground break-all">{status.dshDir}</span>
            </div>
            <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-2">
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">{t("dash.ready")}</dt>
                <dd className={status.ready ? "text-ok" : "text-danger"}>{status.ready ? t("common.yes") : t("common.no")}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">{t("dash.layer")}</dt>
                <dd className="font-mono">{status.manifest?.deployment_id || t("dash.noLayer")}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">{t("dash.adapter")}</dt>
                <dd>
                  <Badge variant={ADAPTER_VARIANT[adapter?.state] || "gray"}>{adapter?.state || "unknown"}</Badge>
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">{t("dash.adapterManaged")}</dt>
                <dd>{adapter?.managed ? t("common.yes") : t("common.no")}</dd>
              </div>
            </dl>
            {status.residue?.length > 0 && (
              <div className="mt-4 rounded-[12px] border border-[var(--danger)] bg-[var(--danger-soft)] p-3">
                <p className="text-xs font-medium text-danger">{t("dash.residue")}</p>
                <ul className="mt-1 space-y-1 font-mono text-xs text-secondary-foreground">
                  {status.residue.map((item, index) => (
                    <li key={index} className="break-all">{item.path} {item.phase ? `(${item.phase})` : ""}</li>
                  ))}
                </ul>
                <Button size="sm" className="mt-2" onClick={() => setView("manage")}>{t("dash.recoverAction")}</Button>
              </div>
            )}
            {status.manifest?.resources && (
              <div className="mt-4 text-xs">
                <h3 className="font-medium text-muted-foreground">{t("dash.resources")}</h3>
                <ul className="mt-1 space-y-1 font-mono text-secondary-foreground">
                  {Object.entries(status.manifest.resources).map(([key, entry]) => (
                    <li key={key} className="break-all">
                      {key}: {(entry?.after_sha256 || "").slice(0, 12) || t("common.none")}
                      {entry?.backup ? ` · bak ${entry.backup}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mt-4">
              <RawJson data={status.raw} />
            </div>
          </section>
        </FadeIn>
      )}
    </div>
  );
}
