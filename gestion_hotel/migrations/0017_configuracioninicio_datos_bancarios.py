from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestion_hotel", "0016_alter_cine_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracioninicio",
            name="banco_1_nombre",
            field=models.CharField(blank=True, max_length=120, null=True, verbose_name="Banco principal: nombre"),
        ),
        migrations.AddField(
            model_name="configuracioninicio",
            name="banco_1_tipo",
            field=models.CharField(blank=True, max_length=80, null=True, verbose_name="Banco principal: tipo de cuenta"),
        ),
        migrations.AddField(
            model_name="configuracioninicio",
            name="banco_1_cuenta",
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="Banco principal: número de cuenta"),
        ),
        migrations.AddField(
            model_name="configuracioninicio",
            name="banco_1_titular",
            field=models.CharField(blank=True, max_length=160, null=True, verbose_name="Banco principal: titular"),
        ),
        migrations.AddField(
            model_name="configuracioninicio",
            name="banco_1_identificacion",
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name="Banco principal: RUC / C.I."),
        ),
        migrations.AddField(
            model_name="configuracioninicio",
            name="banco_1_correo",
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name="Banco principal: correo"),
        ),
    ]
