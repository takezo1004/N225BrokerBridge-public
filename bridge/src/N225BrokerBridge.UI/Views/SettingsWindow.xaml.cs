using System.Windows;
using System.Windows.Controls;
using N225BrokerBridge.UI.ViewModels;
using Wpf.Ui.Controls;

namespace N225BrokerBridge.UI.Views;

public partial class SettingsWindow : FluentWindow
{
    private readonly SettingsViewModel _vm;

    public SettingsWindow(SettingsViewModel vm)
    {
        InitializeComponent();
        _vm = vm;
        DataContext = vm;

        // PasswordBox.Password は SecureString 系で 通常 Binding 不可なので
        // Tag に値をバインドしておき、Loaded で同期 + 変更時に逆同期する
        Loaded += (_, _) =>
        {
            SyncMaskedBoxesFromVm();
        };
        PassphraseBox.PasswordChanged += (_, _) => vm.WebhookPassphrase = PassphraseBox.Password;
        KabuApiPasswordBox.PasswordChanged += (_, _) => vm.KabuApiPassword = KabuApiPasswordBox.Password;
        KabuApiPasswordTestBox.PasswordChanged += (_, _) => vm.KabuApiPasswordTest = KabuApiPasswordTestBox.Password;
        KabuOrderPasswordBox.PasswordChanged += (_, _) => vm.KabuOrderPassword = KabuOrderPasswordBox.Password;

        // 平文表示トグル: マスク→平文 切替時は TextBox の Binding が自動反映する。
        // 平文→マスク 切替時は PasswordBox の値を VM の最新値で再同期する。
        vm.PropertyChanged += (_, args) =>
        {
            if (args.PropertyName == nameof(SettingsViewModel.ShowPasswordsInClear) && !vm.ShowPasswordsInClear)
                SyncMaskedBoxesFromVm();
        };
    }

    /// <summary>VM の現在値で 4 つの PasswordBox を一括上書き。</summary>
    private void SyncMaskedBoxesFromVm()
    {
        PassphraseBox.Password = _vm.WebhookPassphrase ?? string.Empty;
        KabuApiPasswordBox.Password = _vm.KabuApiPassword ?? string.Empty;
        KabuApiPasswordTestBox.Password = _vm.KabuApiPasswordTest ?? string.Empty;
        KabuOrderPasswordBox.Password = _vm.KabuOrderPassword ?? string.Empty;
    }

    private void OnCloseClicked(object sender, RoutedEventArgs e)
    {
        DialogResult = _vm.WasSaved;
        Close();
    }
}
