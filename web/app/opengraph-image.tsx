import { ImageResponse } from "next/og";

import { SITE_URL } from "@/lib/site";

export const dynamic = "force-static";
export const alt = "Cyberyen Explorer — block explorer for the Cyberyen blockchain";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const siteHost = new URL(SITE_URL).host;

const LOGO_PATH =
  "M385 127v25h25v51h51v-51h-25v-50h-51v25m203 0v25h-25v51h51v-51h25v-50h-51v25M410 254v17h-33v34h-34v34h-34v270h34v34h34v34h33v34h204v-34h33v-34h34v-34h34v-67h-68v33h-33v34h-34v34H444v-34h-34v-34h-33V372h33v-33h34v-34h136v34h34v33h33v34h68v-67h-34v-34h-34v-34h-33v-34H410v17m0 503.5V770h76v51h-76v25h75.976l.262 38.25.262 38.25h51l.262-38.25.262-38.25H614v-25h-76v-51h76v-25H410v12.5";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "#000000",
          backgroundImage:
            "radial-gradient(ellipse 80% 60% at 20% 20%, #202020 0%, transparent 55%), radial-gradient(ellipse 70% 50% at 90% 80%, #252525 0%, transparent 50%)",
          padding: "72px 80px",
          color: "#e3e3e3",
          fontFamily:
            "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 20,
          }}
        >
          <svg
            width="72"
            height="72"
            viewBox="0 0 1024 1024"
            fill="none"
          >
            <path d={LOGO_PATH} fill="#6D6D6D" />
          </svg>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            <span
              style={{
                fontSize: 28,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "#6d6d6d",
              }}
            >
              Cyberyen
            </span>
            <span
              style={{
                fontSize: 48,
                fontWeight: 700,
                color: "#ffffff",
                letterSpacing: "-0.02em",
                lineHeight: 1,
              }}
            >
              Explorer
            </span>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 20,
            maxWidth: 820,
          }}
        >
          <div
            style={{
              width: 64,
              height: 2,
              backgroundColor: "#3c3c3c",
            }}
          />
          <span
            style={{
              fontSize: 36,
              lineHeight: 1.35,
              color: "#b1b1b1",
              letterSpacing: "-0.01em",
            }}
          >
            Browse blocks, transactions, addresses, mempool, and MWEB
            activity on the Cyberyen blockchain.
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: "100%",
          }}
        >
          <span
            style={{
              fontSize: 24,
              color: "#6d6d6d",
              letterSpacing: "0.04em",
            }}
          >
            {siteHost}
          </span>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 18px",
              border: "1px solid #3c3c3c",
              borderRadius: 4,
              color: "#b8bec6",
              fontSize: 20,
            }}
          >
            Blocks · Txs · MWEB
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
