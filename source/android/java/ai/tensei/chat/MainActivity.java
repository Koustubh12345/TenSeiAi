package ai.tensei.chat;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;

import java.util.ArrayList;

/**
 * ChatGPT-style single-screen chat with the TenSeiAi model running on-device.
 */
public class MainActivity extends Activity implements PyBridge.Listener {

    private static final int C_BG = 0xFF212121;
    private static final int C_HEADER = 0xFF171717;
    private static final int C_USER = 0xFF2E6B54;
    private static final int C_BOT = 0xFF2F2F2F;
    private static final int C_TXT = 0xFFECECEC;
    private static final int C_MUTED = 0xFF9E9E9E;
    private static final int C_ACCENT = 0xFF10A37F;

    private ListView list;
    private EditText input;
    private Button send;
    private TextView status;
    private ChatAdapter adapter;
    private PyBridge bridge;
    private boolean busy = false;

    private static class Msg {
        final boolean me;
        final String text;

        Msg(boolean me, String text) {
            this.me = me;
            this.text = text;
        }
    }

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        setContentView(buildUi());
        bridge = new PyBridge(this);
        status.setText("Starting TenSeiAi brain\u2026");
        setInputEnabled(false);
        bridge.start(this);
    }

    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(C_BG);
        root.setFitsSystemWindows(true);

        TextView title = new TextView(this);
        title.setText("TenSeiAi");
        title.setTextColor(Color.WHITE);
        title.setTextSize(18f);
        title.setGravity(Gravity.CENTER);
        title.setPadding(dp(16), dp(14), dp(16), dp(14));
        title.setBackgroundColor(C_HEADER);
        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        View divider = new View(this);
        divider.setBackgroundColor(0xFF333333);
        root.addView(divider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        list = new ListView(this);
        list.setBackgroundColor(C_BG);
        list.setDivider(null);
        list.setDividerHeight(0);
        list.setClipToPadding(false);
        list.setPadding(0, dp(8), 0, dp(8));
        adapter = new ChatAdapter();
        list.setAdapter(adapter);
        root.addView(list, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        status = new TextView(this);
        status.setTextColor(C_MUTED);
        status.setTextSize(12f);
        status.setPadding(dp(16), dp(4), dp(16), dp(6));
        status.setBackgroundColor(C_BG);
        root.addView(status, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setBackgroundColor(C_HEADER);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(10), dp(8), dp(10), dp(8));

        input = new EditText(this);
        input.setHint("Message TenSeiAi");
        input.setHintTextColor(0xFF8A8A8A);
        input.setTextColor(C_TXT);
        input.setTextSize(15.5f);
        input.setBackgroundColor(Color.TRANSPARENT);
        input.setInputType(InputType.TYPE_CLASS_TEXT
                | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        input.setImeOptions(EditorInfo.IME_ACTION_SEND);
        input.setMaxLines(4);
        input.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, android.view.KeyEvent e) {
                if (actionId == EditorInfo.IME_ACTION_SEND) {
                    onSend();
                    return true;
                }
                return false;
            }
        });
        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        bar.addView(input, ilp);

        send = new Button(this);
        send.setText("Send");
        send.setAllCaps(false);
        send.setTextSize(14f);
        send.setTextColor(Color.WHITE);
        GradientDrawable sg = new GradientDrawable();
        sg.setColor(C_ACCENT);
        sg.setCornerRadius(dp(20));
        send.setBackground(sg);
        send.setPadding(dp(18), dp(8), dp(18), dp(8));
        send.setStateListAnimator(null);
        send.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                onSend();
            }
        });
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        slp.setMargins(dp(8), 0, 0, 0);
        bar.addView(send, slp);

        root.addView(bar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return root;
    }

    private void setInputEnabled(boolean on) {
        input.setEnabled(on);
        send.setEnabled(on);
        send.setAlpha(on ? 1f : 0.45f);
        if (on) {
            input.requestFocus();
        }
    }

    private void onSend() {
        String q = input.getText().toString().trim();
        if (q.length() == 0 || busy || !bridge.isReady()) {
            return;
        }
        adapter.add(new Msg(true, q));
        input.setText("");
        busy = true;
        setInputEnabled(false);
        status.setText("TenSeiAi is thinking\u2026");
        bridge.ask(q);
    }

    @Override
    public void onStatus(String message) {
        status.setText(message);
    }

    @Override
    public void onReady(String version) {
        status.setText("Ready \u00b7 runs fully on this phone");
        setInputEnabled(true);
        adapter.add(new Msg(false,
                "Hello! I am TenSeiAi, running from the model packed inside "
                        + "this app. Ask me anything."));
    }

    @Override
    public void onAnswer(String answer, String mode, double confidence) {
        busy = false;
        setInputEnabled(true);
        status.setText(mode.length() > 0 ? "Ready \u00b7 " + mode : "Ready");
        adapter.add(new Msg(false, answer));
    }

    @Override
    public void onError(String message) {
        busy = false;
        setInputEnabled(true);
        status.setText("Error");
        adapter.add(new Msg(false, "Error: " + message));
    }

    @Override
    protected void onDestroy() {
        if (bridge != null) {
            bridge.stop();
        }
        super.onDestroy();
    }

    private class ChatAdapter extends BaseAdapter {
        private final ArrayList<Msg> items = new ArrayList<Msg>();

        void add(Msg m) {
            items.add(m);
            notifyDataSetChanged();
            list.post(new Runnable() {
                @Override
                public void run() {
                    list.setSelection(items.size() - 1);
                }
            });
        }

        @Override
        public int getCount() {
            return items.size();
        }

        @Override
        public Object getItem(int i) {
            return items.get(i);
        }

        @Override
        public long getItemId(int i) {
            return i;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            Msg m = items.get(position);
            FrameLayout row = new FrameLayout(MainActivity.this);
            row.setPadding(dp(8), dp(3), dp(8), dp(3));

            TextView tv = new TextView(MainActivity.this);
            tv.setText(m.text);
            tv.setTextColor(C_TXT);
            tv.setTextSize(15.5f);
            tv.setTextIsSelectable(true);
            tv.setLineSpacing(dp(2), 1f);
            GradientDrawable bg = new GradientDrawable();
            bg.setColor(m.me ? C_USER : C_BOT);
            bg.setCornerRadius(dp(16));
            tv.setBackground(bg);
            int p = dp(12);
            tv.setPadding(p, dp(9), p, dp(9));
            int max = (int) (getResources().getDisplayMetrics().widthPixels * 0.82f);
            tv.setMaxWidth(max);

            FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT);
            lp.gravity = m.me ? Gravity.END : Gravity.START;
            row.addView(tv, lp);
            return row;
        }
    }
}
