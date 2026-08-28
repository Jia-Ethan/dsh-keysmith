import React from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useAppState } from "@/hooks/useAppState";
import { getSettings } from "@/lib/settings";
import {
  fetchStatus,
  previewUninstall,
  executeUninstall,
  previewRecover,
  executeRecover,
} from "@/lib/api";
import { FadeIn } from "@/components/FadeIn";
import { ReportView } from "@/components/ReportView";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { setLastStatus } from "@/lib/store";

export function Manage() {
  const { t } = useTranslation();
  const { cliInfo, operationInProgress } = useAppState();
  const [dshDir, setDshDir] = React.useState(() => getSettings().defaultDshDir || "");
  const [status, setStatus] = React.useState(null);
  const [pending, setPending] = React.useState(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [done, setDone] = React.useState(null);

  const options = { dshDir: dshDir.trim() };

  const reload = React.useCallback(async () => {
    if (!cliInfo.path) return;
    try {
      const next = await fetchStatus(options);
      setStatus(next);
      setLastStatus(next);
    } catch (err) {
      toast.error(err?.message || t("manage.failed"));
    }
  }, [cliInfo.path, dshDir, t]); // eslint-disable-line react-hooks/exhaustive-deps

  React.useEffect(() => {
    reload();
  }, [reload]);

  const start = async (kind) => {
    setBusy(true);
    try {
      const preview = kind === "uninstall" ? await previewUninstall(options) : await previewRecover(options);
      setPending({ kind, preview });
      setConfirmOpen(true);
    } catch (err) {
      toast.error(err?.message || t("manage.failed"));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!pending) return;
    setBusy(true);
    try {
      const report = pending.kind === "uninstall"
        ? await executeUninstall(options)
        : await executeRecover(options);
      setDone(report);
      setConfirmOpen(false);
      setPending(null);
      if (report.gate.ok) toast.success(t("manage.done"));
      else toast.error(t("manage.failed"));
      await reload();
    } catch (err) {
      toast.error(err?.message || t("manage.failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <FadeIn>
        <h1 className="text-2xl font-semibold tracking-tight">{t("manage.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("manage.subtitle")}</p>
      </FadeIn>

      <section className="card-glass mt-6 p-5">
        <label className="text-sm font-medium" htmlFor="manage-dir">{t("manage.selectDir")}</label>
        <Input id="manage-dir" className="mt-1.5 font-mono text-xs" value={dshDir} onChange={(e) => setDshDir(e.target.value)} />
        {status && (
          <p className="mt-3 text-xs text-muted-foreground">
            {t("dash.layer")}: {status.manifest?.deployment_id || t("dash.noLayer")}
            {status.residue?.length ? ` · ${t("dash.residue")}` : ""}
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button disabled={busy || operationInProgress || !cliInfo.path} onClick={() => start("uninstall")}>
            {t("manage.uninstall")}
          </Button>
          <Button variant="secondary" disabled={busy || operationInProgress || !cliInfo.path} onClick={() => start("recover")}>
            {t("manage.recover")}
          </Button>
        </div>
      </section>

      {pending?.preview && (
        <section className="card-glass mt-4 p-5">
          <h2 className="text-sm font-medium">{t("manage.previewPlan")}</h2>
          <div className="mt-3">
            <ReportView report={pending.preview} showTarget={false} />
          </div>
        </section>
      )}

      {done && (
        <section className="card-glass mt-4 p-5">
          <h2 className="text-sm font-medium">{t("manage.result")}</h2>
          <div className="mt-3">
            <ReportView report={done} showTarget={false} />
          </div>
        </section>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={pending?.kind === "recover" ? t("manage.confirmRecover") : t("manage.confirmUninstall")}
        body={pending?.kind === "recover" ? t("manage.recoverDesc") : t("manage.uninstallDesc")}
        confirmText={t("manage.execute")}
        confirmDisabled={busy}
        danger={pending?.kind === "uninstall"}
        onConfirm={confirm}
      />
    </div>
  );
}
