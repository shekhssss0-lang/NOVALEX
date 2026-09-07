package com.novalex.app;

import android.Manifest;
import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Notification;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.view.animation.AlphaAnimation;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.os.Handler;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.LinearLayout;

public class MainActivity extends Activity {

    private WebView webView;
    private LinearLayout splash;

    private static final String CHANNEL_ID = "novalex_alerts";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout splash = new LinearLayout(this);
        splash.setOrientation(LinearLayout.VERTICAL);
        splash.setGravity(Gravity.CENTER);
        splash.setBackgroundColor(Color.BLACK);
        splash.setPadding(48, 48, 48, 48);

        ImageView logo = new ImageView(this);
        logo.setImageResource(com.novalex.app.R.drawable.novalex_logo);
        logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE);

        LinearLayout.LayoutParams logoParams =
                new LinearLayout.LayoutParams(260, 260);
        splash.addView(logo, logoParams);

        TextView brand = new TextView(this);
        brand.setText("NOVALEX");
        brand.setTextColor(Color.WHITE);
        brand.setTextSize(28);
        brand.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        brand.setGravity(Gravity.CENTER);
        splash.addView(brand);

        TextView sub = new TextView(this);
        sub.setText("PREMIUM CLOTHING");
        sub.setTextColor(Color.rgb(217,168,63));
        sub.setTextSize(12);
        sub.setLetterSpacing(0.25f);
        sub.setGravity(Gravity.CENTER);
        splash.addView(sub);

        TextView loading = new TextView(this);
        loading.setText("Loading your style...");
        loading.setTextColor(Color.LTGRAY);
        loading.setTextSize(12);
        loading.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams loadParams =
                new LinearLayout.LayoutParams(-1, -2);
        loadParams.topMargin = 36;
        splash.addView(loading, loadParams);

        setContentView(splash);

        AlphaAnimation fade = new AlphaAnimation(0.0f, 1.0f);
        fade.setDuration(900);
        logo.startAnimation(fade);
        brand.startAnimation(fade);
        sub.startAnimation(fade);

        new Handler().postDelayed(() -> {
            setContentView(R.layout.activity_main);
            android.webkit.WebView webView = findViewById(R.id.webview);
            webView.setBackgroundColor(android.graphics.Color.BLACK);
            webView.setOverScrollMode(android.view.View.OVER_SCROLL_NEVER);
            webView.setVerticalScrollBarEnabled(false);
            webView.setHorizontalScrollBarEnabled(false);
            if (webView != null) {
                webView.loadUrl("file:///android_asset/index.html");
            }
        }, 2400);
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();

        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadsImagesAutomatically(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setSupportZoom(false);

        webView.setBackgroundColor(0xFFFFFFFF);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        // Bundled NovaLex storefront
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void setupNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "NovaLex Alerts",
                    NotificationManager.IMPORTANCE_HIGH
            );

            channel.setDescription(
                    "NovaLex new products, sales and important order alerts"
            );

            NotificationManager manager =
                    getSystemService(NotificationManager.class);

            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }

        if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                        != PackageManager.PERMISSION_GRANTED) {

            requestPermissions(
                    new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    1001
            );
        }
    }

    private void showNewDropNotification() {

        if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                        != PackageManager.PERMISSION_GRANTED) {
            return;
        }

        Notification.Builder builder;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        builder.setSmallIcon(R.drawable.ic_novalex)
                .setContentTitle("NOVALEX • NEW DROP")
                .setContentText(
                        "Premium NovaLex styles are now available."
                )
                .setAutoCancel(true)
                .setPriority(Notification.PRIORITY_HIGH);

        NotificationManager manager =
                (NotificationManager) getSystemService(NOTIFICATION_SERVICE);

        if (manager != null) {
            manager.notify(101, builder.build());
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
