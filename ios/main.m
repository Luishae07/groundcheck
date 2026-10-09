// Groundcheck for iPhone and iPad: a full-screen web view of the Groundcheck web app, with location.
#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#import <CoreLocation/CoreLocation.h>

static NSString *const kBase = @"https://luishae07.github.io/groundcheck/";

@interface GCViewController : UIViewController <WKNavigationDelegate, CLLocationManagerDelegate>
@property (nonatomic, strong) WKWebView *web;
@property (nonatomic, strong) CLLocationManager *loc;
@end

@implementation GCViewController

- (NSURL *)appURL {
    BOOL pad = UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad;
    return [NSURL URLWithString:pad ? [kBase stringByAppendingString:@"desktop/"] : kBase];
}

- (void)viewDidLoad {
    [super viewDidLoad];
    UIColor *bg = [UIColor colorWithRed:14/255.0 green:22/255.0 blue:40/255.0 alpha:1];
    self.view.backgroundColor = bg;

    WKWebViewConfiguration *cfg = [WKWebViewConfiguration new];
    cfg.allowsInlineMediaPlayback = YES;
    self.web = [[WKWebView alloc] initWithFrame:CGRectZero configuration:cfg];
    self.web.translatesAutoresizingMaskIntoConstraints = NO;
    self.web.navigationDelegate = self;
    self.web.opaque = NO;
    self.web.backgroundColor = bg;
    self.web.scrollView.backgroundColor = bg;
    self.web.allowsBackForwardNavigationGestures = YES;
    [self.view addSubview:self.web];

    UILayoutGuide *g = self.view.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        [self.web.topAnchor constraintEqualToAnchor:g.topAnchor],
        [self.web.bottomAnchor constraintEqualToAnchor:g.bottomAnchor],
        [self.web.leadingAnchor constraintEqualToAnchor:g.leadingAnchor],
        [self.web.trailingAnchor constraintEqualToAnchor:g.trailingAnchor],
    ]];

    // the page asks for the position with navigator.geolocation; iOS needs the app itself to have asked first
    self.loc = [CLLocationManager new];
    self.loc.delegate = self;
    [self.loc requestWhenInUseAuthorization];

    [self.web loadRequest:[NSURLRequest requestWithURL:[self appURL]]];
}

- (UIStatusBarStyle)preferredStatusBarStyle { return UIStatusBarStyleLightContent; }

// links that leave Groundcheck open in Safari
- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)action
                                                     decisionHandler:(void (^)(WKNavigationActionPolicy))handler {
    NSURL *u = action.request.URL;
    if (action.navigationType == WKNavigationTypeLinkActivated && u.host &&
        ![u.host isEqualToString:[self appURL].host]) {
        [UIApplication.sharedApplication openURL:u options:@{} completionHandler:nil];
        handler(WKNavigationActionPolicyCancel);
        return;
    }
    handler(WKNavigationActionPolicyAllow);
}

- (void)showOffline {
    NSString *html = [NSString stringWithFormat:
        @"<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<body style='font:17px -apple-system;background:#0e1628;color:#ecf0ff;text-align:center;padding:30vh 24px 0'>"
        "<h2>Can't reach Groundcheck</h2><p style='color:#8c92b0'>Check your connection.</p>"
        "<p><a href='%@' style='color:#7c8cff;font-size:19px'>Try again</a></p></body>", [self appURL].absoluteString];
    [self.web loadHTMLString:html baseURL:[NSURL URLWithString:kBase]];
}

- (void)webView:(WKWebView *)w didFailProvisionalNavigation:(WKNavigation *)n withError:(NSError *)e { [self showOffline]; }
- (void)webView:(WKWebView *)w didFailNavigation:(WKNavigation *)n withError:(NSError *)e { [self showOffline]; }
- (void)locationManagerDidChangeAuthorization:(CLLocationManager *)manager {}

@end

@interface GCAppDelegate : UIResponder <UIApplicationDelegate>
@property (nonatomic, strong) UIWindow *window;
@end

@implementation GCAppDelegate
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)opts {
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    self.window.rootViewController = [GCViewController new];
    [self.window makeKeyAndVisible];
    return YES;
}
@end

int main(int argc, char *argv[]) {
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil, NSStringFromClass([GCAppDelegate class]));
    }
}
