(() => {
  try {
    window.__ModuleLoader__.load({
      id: "dsh-keysmith",
      factory: (require) => {
        var module = { exports: {} };
        var exports = module.exports;
        Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });

        var react = require("react");
        var inject = ["slots"];

        var WRAP_STYLE = {
          display: "flex",
          justifyContent: "center",
          width: "100%",
        };
        var BADGE_STYLE = {
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          width: "fit-content",
          padding: "3px 10px",
          borderRadius: "6px",
          border: "1px solid rgba(99, 102, 241, 0.45)",
          background: "rgba(99, 102, 241, 0.12)",
          color: "inherit",
          fontSize: "11px",
          lineHeight: "16px",
          fontFamily: "inherit",
          userSelect: "none",
          whiteSpace: "nowrap",
        };
        var DOT_STYLE = {
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          background: "#6366f1",
          flex: "none",
        };

        function KeysmithDock(props) {
          var useProjection = props.useProjection;
          var state =
            typeof useProjection === "function" ? useProjection("dsh-keysmith") : undefined;
          var active = !(state && state.active === false);
          var text = active ? "Keysmith 已激活" : "Keysmith 未激活";
          return react.createElement(
            "div",
            { style: WRAP_STYLE },
            react.createElement(
              "div",
              {
                style: BADGE_STYLE,
                "data-keysmith": active ? "on" : "off",
                "data-plugin": "dsh-keysmith",
                title: "dsh-keysmith assemble guard + delivery contract",
              },
              react.createElement("span", { style: DOT_STYLE }),
              react.createElement("span", null, text),
            ),
          );
        }

        function apply(ctx) {
          ctx.slots.inject("conversation.input.dock", () =>
            ctx.slots.register(
              {
                name: "conversation.input.dock",
                id: "dsh-keysmith:badge",
                order: 20,
              },
              KeysmithDock,
            ),
          );
        }

        exports.name = "dsh-keysmith";
        exports.inject = inject;
        exports.apply = apply;
        return module.exports;
      },
    });
  } catch (err) {
    console.warn("[dsh-keysmith] client runtime error:", err);
  }
})();
